from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import aiohttp
from typing import List, Optional, Dict, Any
import asyncio

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

def merge_data(stations: Dict[str, Any], artworks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    station_dict = {
        feature['properties']['station_id']: feature['properties'] 
        for feature in stations['features']
    }
    merged_artworks = []

    for artwork in artworks:
        station_name = artwork.get('station_name')
        matching_stations = [
            s for s in station_dict.values() 
            if s.get('stop_name', '').lower() == station_name.lower()
        ]
        
        if matching_stations:
            # Use the first matching station's location
            station = matching_stations[0]
            artwork_feature = {
                "art_id": artwork.get('id'),
                "station_name": station_name,
                "artist": artwork.get('artist'),
                "art_title": artwork.get('art_title'),
                "art_date": artwork.get('art_date'),
                "art_material": artwork.get('art_material'),
                "art_description": artwork.get('art_description'),
                "art_image_link": {"url": artwork.get('art_image_link', {}).get('url')},
                "latitude": float(station.get('gtfs_latitude')),
                "longitude": float(station.get('gtfs_longitude')),
                "related_stations": [
                    {
                        "station_id": s.get('station_id', ''),
                        "line": s.get('daytime_routes', ''),
                        "borough": s.get('borough', '')
                    } for s in matching_stations
                ]
            }
            merged_artworks.append(artwork_feature)

    return merged_artworks

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)