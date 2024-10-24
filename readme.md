# NYC Subway Art Explorer Backend
This project is the frontend for the [NYC Subway Art Explorer](https://nycsubwayartexplorer.app/), a web application that visualizes artwork installations in New York City subway stations.

This application runs using the [NYC Transit Art Explorer Frontend](https://github.com/rcoulterGIS/artmapfrontend). The frontend can be deployed locally for testing purposes. See the repository for details. 

# Setup

## Prerequisites
Python 3.12 \
pip (Python package installer) \
venv 

## Clone the repository and navigate to the backend directory:
### `cd backend`

## Create virtual environment:
### `python -m venv venv`
### `source venv/bin/activate`

## Install Dependencies:
### `pip install -r requirements.txt`

## Run Tests
### `cd app`
### `pytest test_main.py`

## Start Development Server:
### `uvicorn app.main:app --reload`
The app will run on http://localhost:8000.


## API Endpoints
### GET /: Welcome message
### GET /artworks: List all artworks (optional borough filter)
### Response Schema
[
  {
    "art_id": "string",
    "station_name": "string",
    "artist": "string",
    "art_title": "string",
    "art_date": "string",
    "art_material": "string",
    "art_description": "string",
    "art_image_link": {
      "url": "string"
    },
    "latitude": 0,
    "longitude": 0,
    "related_stations": [
      {
        "station_id": "string",
        "line": "string",
        "borough": "string"
      }
    ]
  }
]
### GET /artworks/{art_id}: Get details of a specific artwork
### Response Schema
{
  "art_id": "string",
  "station_name": "string",
  "artist": "string",
  "art_title": "string",
  "art_date": "string",
  "art_material": "string",
  "art_description": "string",
  "art_image_link": {
    "url": "string"
  },
  "latitude": 0,
  "longitude": 0,
  "related_stations": [
    {
      "station_id": "string",
      "line": "string",
      "borough": "string"
    }
  ]
}

### GET /stations-with-art: List all stations with artwork (optional borough filter)
### Response Schema
[
  {
    "station_id": "string",
    "station_name": "string",
    "latitude": 0,
    "longitude": 0,
    "borough": "string",
    "lines": "string",
    "artwork_count": 0,
    "artworks": [
      {
        "art_id": "string",
        "art_title": "string",
        "artist": "string",
        "art_description": "string",
        "art_image_link": {
          "url": "string"
        }
      }
    ]
  }
]

## Data Sources
The application sources data from the [NYC Open Data Catalog](https://opendata.cityofnewyork.us/). [Station Locations](https://data.ny.gov/Transportation/MTA-Subway-Stations-Map/p6ps-59h2) were sourced from the following URL:
### `https://data.ny.gov/resource/39hk-dx4f.geojson`

[The MTA Permanent Art Catalog](https://data.ny.gov/Transportation/MTA-Permanent-Art-Catalog-Beginning-1980/4y8j-9pkd/about_data)   served as the source for artwork information including artwork name, year, artist, material, and descriptions. Data was sourced from the following URL:
### `https://data.ny.gov/resource/4y8j-9pkd.json`

## Data Processing
Data from the two sources is joined on station name and service lines, accomodating for the duplicate station name values across different stations.

## CI/CD
The production backend of the application [https://nycsubwayartexplorer.app/](https://nycsubwayartexplorer.app/) is continuously integrated and deployed via Github Actions. Upon git push test_main.py is automatically run in a test environment hosted by Github. Upon successful completion of the tests, a build is triggered on [Heroku](https://dashboard.heroku.com/apps), the backend cloud hosting platform selected for this project. For more information about GitHub Actions, click [here](https://github.com/features/actions), and for integrating Heroku deployments with your CI/CD pipelines, click [here](https://www.heroku.com/continuous-integration).