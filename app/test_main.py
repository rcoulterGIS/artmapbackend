import pytest
from httpx import AsyncClient
from main import app, fetch_all_data
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
                    "stop_name": "Test Station",
                    "daytime_routes": "A",
                    "borough": "M",
                    "gtfs_latitude": "40.7",
                    "gtfs_longitude": "-74.0"
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [-74.0, 40.7]
                }
            }
        ]
    }
    mock_artworks_data = [
        {
            "id": "1",
            "station_name": "Test Station",
            "artist": "Test Artist 1",
            "art_title": "Test Artwork 1",
            "art_image_link": {"url": "https://example.com/image1.jpg"}
        },
        {
            "id": "2",
            "station_name": "Test Station",
            "artist": "Test Artist 2",
            "art_title": "Test Artwork 2",
            "art_image_link": {"url": "https://example.com/image2.jpg"}
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
    assert len(artworks) == 2
    assert all(isinstance(artwork, dict) for artwork in artworks)
    assert all('station_name' in artwork for artwork in artworks)
    assert all('art_image_link' in artwork and isinstance(artwork['art_image_link'], dict) for artwork in artworks)
    assert all('latitude' in artwork and 'longitude' in artwork for artwork in artworks)

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
    assert len(artworks) == 2
    assert artworks[0]['station_name'] == artworks[1]['station_name']
    assert artworks[0]['latitude'] != artworks[1]['latitude'] or artworks[0]['longitude'] != artworks[1]['longitude']