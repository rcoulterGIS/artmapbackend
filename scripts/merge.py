import json

def load_json(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)

def merge_json_to_geojson(stations_file, arts_file, output_file):
    # Load the JSON files
    stations_data = load_json(stations_file)
    arts_data = load_json(arts_file)

    # Create a dictionary to store art information by station name
    art_by_station = {art['station_name']: art for art in arts_data}

    # Create the GeoJSON structure
    geojson = {
        "type": "FeatureCollection",
        "features": []
    }

    # Merge the data
    for feature in stations_data['features']:
        station_name = feature['properties']['stop_name']
        if station_name in art_by_station:
            art_info = art_by_station[station_name]
            # Merge art information into the station properties
            art_properties = {
                "artist": art_info.get('artist'),
                "art_title": art_info.get('art_title'),
                "art_date": art_info.get('art_date'),
                "art_material": art_info.get('art_material'),
                "art_description": art_info.get('art_description'),
            }
            
            # Handle 'art_image_link' separately due to its potentially nested structure
            if 'art_image_link' in art_info:
                if isinstance(art_info['art_image_link'], dict):
                    art_properties["art_image_link"] = art_info['art_image_link'].get('url')
                else:
                    art_properties["art_image_link"] = art_info['art_image_link']
            
            feature['properties'].update(art_properties)
        geojson['features'].append(feature)

    # Write the merged GeoJSON to a file
    with open(output_file, 'w') as f:
        json.dump(geojson, f, indent=2)

    print(f"Merged GeoJSON file created: {output_file}")

# Usage
stations_file = '../data/stations.geojson'
arts_file = '../data/art.json'
output_file = '../data/merged_stations_art.geojson'

merge_json_to_geojson(stations_file, arts_file, output_file)