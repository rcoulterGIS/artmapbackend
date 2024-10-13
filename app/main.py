from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import aiohttp
from typing import List, Optional, Dict, Any
import asyncio
import random
import math

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

class StationWithArtworks(BaseModel):
    station_id: str
    station_name: str
    latitude: float
    longitude: float
    borough: str
    lines: str
    artwork_count: int
    artworks: List[Artwork]
    zoom_level: float = 15

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
                station['artworks'].append(Artwork(
                    art_id=artwork.get('id'),
                    station_name=station_name,
                    art_title=artwork.get('art_title'),
                    artist=artwork.get('artist'),
                    art_date=artwork.get('art_date'),
                    art_material=artwork.get('art_material'),
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
    merged_data = aggregate_station_data(stations_data, artworks_data)
    
    if borough:
        merged_data = [
            station for station in merged_data
            if station.borough == borough
        ]
    
    all_artworks = [artwork for station in merged_data for artwork in station.artworks]
    return all_artworks

@app.get("/artworks/{art_id}", response_model=Artwork)
async def get_artwork(art_id: str):
    stations_data, artworks_data = await fetch_all_data()
    merged_data = aggregate_station_data(stations_data, artworks_data)
    
    for station in merged_data:
        for artwork in station.artworks:
            if artwork.art_id == art_id:
                return artwork
    
    raise HTTPException(status_code=404, detail="Artwork not found")

@app.get("/stations-with-art", response_model=List[StationWithArtworks])
async def get_stations_with_art(
    borough: Optional[str] = Query(None, description="Filter by borough (M, Bk, Bx, Q)")
):
    stations_data, artworks_data = await fetch_all_data()
    aggregated_data = aggregate_station_data(stations_data, artworks_data)
    
    if borough:
        aggregated_data = [station for station in aggregated_data if station.borough == borough]
    
    return aggregated_data

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)