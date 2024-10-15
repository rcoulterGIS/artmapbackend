import pytest
from httpx import AsyncClient
from main import app, fetch_all_data, StationWithArtworks, Artwork, sanitize_text, merge_data
from unittest.mock import patch
from httpx import ASGITransport

pytest_plugins = ('pytest_asyncio',)

@pytest.fixture
async def mock_fetch_all_data():
    mock_stations_data = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "station_id": "1",
                    "stop_name": "Test StationÒ 1",
                    "daytime_routes": "A",
                    "borough": "M",
                    "gtfs_latitude": "40.7",
                    "gtfs_longitude": "-74.0"
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [-74.0, 40.7]
                }
            },
            {
                "type": "Feature",
                "properties": {
                    "station_id": "2",
                    "stop_name": "Test StationÓ 2",
                    "daytime_routes": "B",
                    "borough": "Bk",
                    "gtfs_latitude": "40.8",
                    "gtfs_longitude": "-73.9"
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [-73.9, 40.8]
                }
            }
        ]
    }
    mock_artworks_data = [
        {
            "id": "1",
            "station_name": "Test StationÒ 1",
            "artist": "Test ArtistÉ 1",
            "art_title": "Test ArtworkÂ 1",
            "art_date": "2000",
            "art_material": "Paint",
            "art_description": "A beautiful paintingÒ with random charactersÓ",
            "art_image_link": {"url": "https://example.com/image1.jpg"}
        },
        {
            "id": "2",
            "station_name": "Test StationÒ 1",
            "artist": "Test Artist 2",
            "art_title": "Test Artwork 2",
            "art_date": "2010",
            "art_material": "Sculpture",
            "art_description": "An impressive sculptureÓ\nwith newlines",
            "art_image_link": {"url": "https://example.com/image2.jpg"}
        },
        {
            "id": "3",
            "station_name": "Test StationÓ 2",
            "artist": "Test Artist 3",
            "art_title": "Test Artwork 3",
            "art_date": "2020",
            "art_material": "Mosaic",
            "art_description": "A colorful mosaicÉ",
            "art_image_link": {"url": "https://example.com/image3.jpg"}
        }
    ]
    return (mock_stations_data, mock_artworks_data)

@pytest.fixture
async def async_client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")

@pytest.mark.asyncio
async def test_root(async_client):
    response = await async_client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to the NYC Subway Art API"}

@pytest.mark.asyncio
async def test_get_artworks(async_client, mock_fetch_all_data):
    with patch('main.fetch_all_data', return_value=mock_fetch_all_data):
        response = await async_client.get("/artworks")
    assert response.status_code == 200
    artworks = response.json()
    assert len(artworks) == 3
    assert all(isinstance(artwork, dict) for artwork in artworks)
    assert all('station_name' in artwork for artwork in artworks)
    assert all('art_image_link' in artwork and isinstance(artwork['art_image_link'], dict) for artwork in artworks)
    assert all('latitude' in artwork and 'longitude' in artwork for artwork in artworks)
    assert all('"' not in artwork['station_name'] for artwork in artworks)
    assert all('Ò' not in artwork['art_description'] and 'Ó' not in artwork['art_description'] for artwork in artworks)

@pytest.mark.asyncio
async def test_get_artworks_with_filter(async_client, mock_fetch_all_data):
    with patch('main.fetch_all_data', return_value=mock_fetch_all_data):
        response = await async_client.get("/artworks?borough=M")
    assert response.status_code == 200
    artworks = response.json()
    assert all(any(station['borough'] == 'M' for station in artwork['related_stations']) for artwork in artworks)

@pytest.mark.asyncio
async def test_get_artwork_by_id(async_client, mock_fetch_all_data):
    with patch('main.fetch_all_data', return_value=mock_fetch_all_data):
        response = await async_client.get("/artworks/1")
    assert response.status_code == 200
    artwork = response.json()
    assert artwork["art_id"] == "1"
    assert isinstance(artwork["art_image_link"], dict)
    assert '"' not in artwork['station_name']
    assert 'Ò' not in artwork['art_description'] and 'Ó' not in artwork['art_description']

@pytest.mark.asyncio
async def test_get_artwork_not_found(async_client, mock_fetch_all_data):
    with patch('main.fetch_all_data', return_value=mock_fetch_all_data):
        response = await async_client.get("/artworks/nonexistent_id")
    assert response.status_code == 404
    assert response.json() == {"detail": "Artwork not found"}

@pytest.mark.asyncio
async def test_multiple_artworks_per_station(async_client, mock_fetch_all_data):
    with patch('main.fetch_all_data', return_value=mock_fetch_all_data):
        response = await async_client.get("/artworks")
    assert response.status_code == 200
    artworks = response.json()
    station_1_artworks = [a for a in artworks if a['station_name'] == 'Test Station 1']
    assert len(station_1_artworks) == 2
    assert station_1_artworks[0]['latitude'] != station_1_artworks[1]['latitude'] or \
           station_1_artworks[0]['longitude'] != station_1_artworks[1]['longitude']

@pytest.mark.asyncio
async def test_get_stations_with_art(async_client, mock_fetch_all_data):
    with patch('main.fetch_all_data', return_value=mock_fetch_all_data):
        response = await async_client.get("/stations-with-art")
    assert response.status_code == 200
    stations = response.json()
    assert len(stations) == 2
    assert all(isinstance(station, dict) for station in stations)
    assert all('station_name' in station for station in stations)
    assert all('artwork_count' in station for station in stations)
    assert all('artworks' in station for station in stations)
    assert stations[0]['artwork_count'] == 2
    assert stations[1]['artwork_count'] == 1
    assert all('"' not in station['station_name'] for station in stations)

@pytest.mark.asyncio
async def test_get_stations_with_art_borough_filter(async_client, mock_fetch_all_data):
    with patch('main.fetch_all_data', return_value=mock_fetch_all_data):
        response = await async_client.get("/stations-with-art?borough=M")
    assert response.status_code == 200
    stations = response.json()
    assert len(stations) == 1
    assert stations[0]['borough'] == 'M'
    assert stations[0]['artwork_count'] == 2

@pytest.mark.asyncio
async def test_station_with_artworks_model():
    station = StationWithArtworks(
        station_id="1",
        station_name="Test Station",
        latitude=40.7,
        longitude=-74.0,
        borough="M",
        lines="A",
        artwork_count=2,
        artworks=[
            {"art_id": "1", "art_title": "Artwork 1", "artist": "Artist 1"},
            {"art_id": "2", "art_title": "Artwork 2", "artist": "Artist 2"}
        ]
    )
    assert station.station_id == "1"
    assert station.station_name == "Test Station"
    assert station.latitude == 40.7
    assert station.longitude == -74.0
    assert station.borough == "M"
    assert station.lines == "A"
    assert station.artwork_count == 2
    assert len(station.artworks) == 2
    assert station.artworks[0].art_id == "1"
    assert station.artworks[1].art_title == "Artwork 2"

@pytest.mark.asyncio
async def test_artwork_model():
    artwork = Artwork(
        art_id="1",
        station_name="Test Station",
        artist="Test Artist",
        art_title="Test Artwork",
        art_date="2000",
        art_material="Paint",
        art_description="A beautiful painting",
        art_image_link={"url": "https://example.com/image.jpg"},
        latitude=40.7,
        longitude=-74.0,
        related_stations=[{"station_id": "1", "line": "A", "borough": "M"}]
    )
    assert artwork.art_id == "1"
    assert artwork.station_name == "Test Station"
    assert artwork.artist == "Test Artist"
    assert artwork.art_title == "Test Artwork"
    assert artwork.art_date == "2000"
    assert artwork.art_material == "Paint"
    assert artwork.art_description == "A beautiful painting"
    assert artwork.art_image_link.url == "https://example.com/image.jpg"
    assert artwork.latitude == 40.7
    assert artwork.longitude == -74.0
    assert len(artwork.related_stations) == 1
    assert artwork.related_stations[0].station_id == "1"
    assert artwork.related_stations[0].line == "A"
    assert artwork.related_stations[0].borough == "M"

def test_sanitize_text():
    assert sanitize_text("Test StationÒ") == 'Test Station'  
    assert sanitize_text("Test ArtistÉ") == 'Test Artist'
    assert sanitize_text("Test ArtworkÂ") == 'Test Artwork'
    assert sanitize_text("A beautiful paintingÒ with random charactersÓ") == 'A beautiful painting with random characters'  
    assert sanitize_text("An impressive sculptureÓ\nwith newlines") == 'An impressive sculpture with newlines'  
    assert sanitize_text(None) == None
    assert sanitize_text(123) == 123

@pytest.mark.asyncio
async def test_merge_data_with_sanitization(mock_fetch_all_data):
    stations_data, artworks_data = mock_fetch_all_data
    merged_data = merge_data(stations_data, artworks_data)
    
    assert len(merged_data) == 3
    assert merged_data[0]['station_name'] == 'Test Station 1'
    assert merged_data[0]['artist'] == 'Test Artist 1'  
    assert merged_data[0]['art_title'] == 'Test Artwork 1'  
    assert merged_data[0]['art_description'] == 'A beautiful painting with random characters' 
    assert merged_data[1]['art_description'] == 'An impressive sculpture with newlines'  
    assert all('"' not in artwork['station_name'] for artwork in merged_data)
    assert all('Ò' not in artwork['art_description'] and 'Ó' not in artwork['art_description'] for artwork in merged_data)
