from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import aiohttp
from typing import List, Optional, Dict, Any
import asyncio
import random
import math
import re

app = FastAPI(title="NYC Subway Art API")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API endpoints
STATIONS_API = "https://data.ny.gov/resource/39hk-dx4f.geojson"
ARTWORKS_API = "https://data.ny.gov/resource/4y8j-9pkd.json"

# Pydantic models for response
class RelatedStation(BaseModel):
    station_id: str
    line: str
    borough: Optional[str] = None

class ArtImageLink(BaseModel):
    url: Optional[str] = None

class Artwork(BaseModel):
    art_id: Optional[str] = None
    station_name: str
    artist: Optional[str] = None
    art_title: Optional[str] = None
    art_date: Optional[str] = None
    art_material: Optional[str] = None
    art_description: Optional[str] = None
    art_image_link: Optional[ArtImageLink] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    related_stations: List[RelatedStation] = Field(default_factory=list)

class ArtworkSummary(BaseModel):
    art_id: Optional[str] = None
    art_title: Optional[str] = None
    artist: Optional[str] = None
    art_description: Optional[str] = None
    art_image_link: Optional[ArtImageLink] = None

class StationWithArtworks(BaseModel):
    station_id: str
    station_name: str
    latitude: float
    longitude: float
    borough: Optional[str] = None
    lines: str
    artwork_count: int
    artworks: List[ArtworkSummary]

async def fetch_data(session: aiohttp.ClientSession, url: str) -> Dict[str, Any]:
    async with session.get(url) as response:
        return await response.json()

async def fetch_all_data():
    async with aiohttp.ClientSession() as session:
        stations_data, artworks_data = await asyncio.gather(
            fetch_data(session, STATIONS_API),
            fetch_data(session, ARTWORKS_API)
        )
    return stations_data, artworks_data

def offset_coordinates(lat: float, lon: float, index: int) -> tuple[float, float]:
    offset = (index + 1) * 0.0001
    angle = random.uniform(0, 2 * math.pi)
    lat_offset = offset * math.cos(angle)
    lon_offset = offset * math.sin(angle)
    return lat + lat_offset, lon + lon_offset


def sanitize_text(text):
    if not isinstance(text, str):
        return text
    
    # Remove or replace problematic characters
    text = re.sub(r'[^\x00-\x7F]+', '', text)  # Remove non-ASCII characters
    text = text.replace('Ò', '"').replace('Ó', '"')  # Replace curly quotes
    text = text.replace('É', 'E').replace('é', 'e')  # Replace accented E
    text = text.replace('Â', 'A').replace('â', 'a')  # Replace accented A
    text = text.replace('\n', ' ').replace('\r', '')  # Remove newlines and carriage returns
    
    # Remove extra spaces
    text = ' '.join(text.split())
    
    return text




def merge_data(stations: Dict[str, Any], artworks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    station_dict = {
        feature['properties']['station_id']: {
            **feature['properties'],
            'latitude': float(feature['properties']['gtfs_latitude']),
            'longitude': float(feature['properties']['gtfs_longitude'])
        }
        for feature in stations['features']
    }
    merged_artworks = []
    station_artwork_count = {}

    def normalize_line(line: str) -> set:
        if not line:
            return set()
        
        # Standardize line names
        line = (line.upper()
                .replace('ACE', 'A,C,E')
                .replace('BDFM', 'B,D,F,M')
                .replace('NQR', 'N,Q,R')
                .replace('NQRW', 'N,Q,R,W')
                .replace('JZ', 'J,Z'))
        
        # Split on common separators
        return {p.strip() for p in re.split(r'[,\s/-]+', line) if p.strip()}

    def get_exact_station_match(artwork: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        station_name = sanitize_text(artwork.get('station_name', ''))
        artwork_lines = normalize_line(artwork.get('line', ''))
        
        if not artwork_lines:  # If artwork has no line info, we can't make an exact match
            return None
            
        # Find station with matching name AND at least one matching line
        for station in station_dict.values():
            if (sanitize_text(station.get('stop_name', '')).lower() == station_name.lower()):
                station_lines = normalize_line(station.get('daytime_routes', ''))
                if bool(artwork_lines & station_lines):  # Check for any common lines
                    return station
        
        return None

    for artwork in artworks:
        matching_station = get_exact_station_match(artwork)
        
        if matching_station:
            # Get base coordinates from matched station
            base_lat = matching_station['latitude']
            base_lon = matching_station['longitude']
            
            # Track artwork count for this specific station
            count_key = matching_station['station_id']
            artwork_count = station_artwork_count.get(count_key, 0)
            station_artwork_count[count_key] = artwork_count + 1
            
            # Calculate coordinates with offset if needed
            lat, lon = (base_lat, base_lon) if artwork_count == 0 else offset_coordinates(base_lat, base_lon, artwork_count)

            artwork_feature = {
                "art_id": artwork.get('id'),
                "station_name": sanitize_text(artwork.get('station_name', '')),
                "artist": sanitize_text(artwork.get('artist')),
                "art_title": sanitize_text(artwork.get('art_title')),
                "art_date": sanitize_text(artwork.get('art_date')),
                "art_material": sanitize_text(artwork.get('art_material')),
                "art_description": sanitize_text(artwork.get('art_description')),
                "art_image_link": {"url": artwork.get('art_image_link', {}).get('url')},
                "latitude": lat,
                "longitude": lon,
                "related_stations": [{
                    "station_id": matching_station.get('station_id', ''),
                    "line": sanitize_text(matching_station.get('daytime_routes', '')),
                    "borough": sanitize_text(matching_station.get('borough', ''))
                }]
            }
            merged_artworks.append(artwork_feature)

    return merged_artworks

def aggregate_station_data(stations: Dict[str, Any], artworks: List[Dict[str, Any]]) -> List[StationWithArtworks]:
    station_dict = {
        feature['properties']['station_id']: {
            **feature['properties'],
            'latitude': float(feature['properties']['gtfs_latitude']),
            'longitude': float(feature['properties']['gtfs_longitude']),
            'artworks': []
        }
        for feature in stations['features']
    }

    for artwork in artworks:
        station_name = artwork.get('station_name')
        matching_stations = [
            s for s in station_dict.values() 
            if s['stop_name'].lower() == station_name.lower()
        ]
        
        if matching_stations:
            for station in matching_stations:
                station['artworks'].append(ArtworkSummary(
                    art_id=artwork.get('id'),
                    art_title=artwork.get('art_title'),
                    artist=artwork.get('artist'),
                    art_description=artwork.get('art_description'),
                    art_image_link=ArtImageLink(url=artwork.get('art_image_link', {}).get('url'))
                ))

    return [
        StationWithArtworks(
            station_id=station['station_id'],
            station_name=station['stop_name'],
            latitude=station['latitude'],
            longitude=station['longitude'],
            borough=station.get('borough'),
            lines=station.get('daytime_routes', ''),
            artwork_count=len(station['artworks']),
            artworks=station['artworks']
        )
        for station in station_dict.values()
        if station['artworks']
    ]

@app.get("/")
async def root():
    return {"message": "Welcome to the NYC Subway Art API"}

@app.get("/artworks", response_model=List[Artwork])
async def get_artworks(
    borough: Optional[str] = Query(None, description="Filter by borough (M, Bk, Bx, Q)")
):
    stations_data, artworks_data = await fetch_all_data()
    merged_data = merge_data(stations_data, artworks_data)
    
    if borough:
        merged_data = [
            artwork for artwork in merged_data
            if any(station['borough'] == borough for station in artwork["related_stations"])
        ]
    
    return [Artwork(**artwork) for artwork in merged_data]

@app.get("/artworks/{art_id}", response_model=Artwork)
async def get_artwork(art_id: str):
    stations_data, artworks_data = await fetch_all_data()
    merged_data = merge_data(stations_data, artworks_data)
    
    for artwork in merged_data:
        if artwork["art_id"] == art_id:
            return Artwork(**artwork)
    
    raise HTTPException(status_code=404, detail="Artwork not found")

@app.get("/stations-with-art", response_model=List[StationWithArtworks])
async def get_stations_with_art(
    borough: Optional[str] = Query(None, description="Filter by borough (M, Bk, Bx, Q)")
):
    stations_data, artworks_data = await fetch_all_data()
    aggregated_data = aggregate_station_data(stations_data, artworks_data)
    
    if borough:
        aggregated_data = [
            station for station in aggregated_data
            if station.borough == borough
        ]
    
    return aggregated_data

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)