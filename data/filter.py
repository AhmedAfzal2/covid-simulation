# for filtering airport data, for less dense appearance
import csv
import math

R = 6378317     # radius of earth in meters, for conversion of coordinates

def convert_coords(lat, lon):
    # conversion of latitude, longitude coordinates on a Mercator projection to x, y
    
    MAX_LAT = 85.05112878
    lat = max(min(lat, MAX_LAT), -MAX_LAT)
    
    x = R * math.radians(lon)
    y = R * math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))
    return x, y
    
CELL_SIZE = 1000000
with open('data/airports.csv', 'r') as file:
    reader = csv.reader(file)
    filtered = []
    hashmap = set()
        
    for row in reader:
        x, y = convert_coords(float(row[1]), float(row[2]))
        grid_x = x // CELL_SIZE
        grid_y = y // CELL_SIZE
        
        if (grid_x, grid_y) not in hashmap:
            hashmap.add((grid_x, grid_y))
            filtered.append(row[1:])
    
    with open('data/filtered_airports.csv', 'w', newline='') as wr:
        writer = csv.writer(wr)
        writer.writerows(filtered)  