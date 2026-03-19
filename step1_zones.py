"""
STEP 1: Define Delhi Zones
Each zone = one geographic unit for safety scoring and routing
"""

import pandas as pd
import json

# Delhi's 70 key localities used as zones
# These match the kind of areas shown in your UI (Greater Kailash, Rohini etc.)
# lat/lng = centroid of each zone

DELHI_ZONES = [
    # Zone Name,               Lat,      Lng,     District,         Type
    ("Chandni Chowk",          28.6507,  77.2300, "Central Delhi",  "Commercial"),
    ("Paharganj",              28.6438,  77.2120, "Central Delhi",  "Commercial"),
    ("Karol Bagh",             28.6519,  77.1909, "Central Delhi",  "Commercial"),
    ("Connaught Place",        28.6315,  77.2167, "New Delhi",      "Commercial"),
    ("Nehru Place",            28.5491,  77.2510, "South Delhi",    "Commercial"),
    ("Lajpat Nagar",           28.5677,  77.2433, "South Delhi",    "Residential"),
    ("Greater Kailash",        28.5380,  77.2310, "South Delhi",    "Residential"),
    ("Saket",                  28.5244,  77.2090, "South Delhi",    "Residential"),
    ("Vasant Kunj",            28.5200,  77.1570, "South West Delhi","Residential"),
    ("Dwarka",                 28.5921,  77.0460, "South West Delhi","Residential"),
    ("Rohini",                 28.7380,  77.1050, "North West Delhi","Residential"),
    ("Pitampura",              28.7020,  77.1310, "North West Delhi","Residential"),
    ("Janakpuri",              28.6286,  77.0840, "West Delhi",     "Residential"),
    ("Rajouri Garden",         28.6470,  77.1210, "West Delhi",     "Residential"),
    ("Uttam Nagar",            28.6200,  77.0590, "West Delhi",     "Residential"),
    ("Tilak Nagar",            28.6411,  77.1030, "West Delhi",     "Residential"),
    ("Shahdara",               28.6700,  77.2920, "Shahdara",       "Residential"),
    ("Preet Vihar",            28.6425,  77.2960, "Shahdara",       "Residential"),
    ("Vivek Vihar",            28.6710,  77.3140, "Shahdara",       "Residential"),
    ("Patparganj",             28.6270,  77.2960, "East Delhi",     "Residential"),
    ("Mayur Vihar",            28.6075,  77.2950, "East Delhi",     "Residential"),
    ("Laxmi Nagar",            28.6328,  77.2779, "East Delhi",     "Commercial"),
    ("Geeta Colony",           28.6550,  77.2720, "East Delhi",     "Residential"),
    ("Seemapuri",              28.6890,  77.3230, "Shahdara",       "Residential"),
    ("Mustafabad",             28.7160,  77.3010, "North East Delhi","Residential"),
    ("Bhajanpura",             28.6980,  77.2810, "North East Delhi","Residential"),
    ("Welcome Colony",         28.6830,  77.2920, "North East Delhi","Residential"),
    ("Seelampur",              28.6720,  77.2780, "North East Delhi","Residential"),
    ("Yamuna Vihar",           28.7020,  77.2920, "North East Delhi","Residential"),
    ("Burari",                 28.7450,  77.2100, "North Delhi",    "Residential"),
    ("Model Town",             28.7150,  77.1940, "North Delhi",    "Residential"),
    ("Civil Lines",            28.6900,  77.2230, "North Delhi",    "Residential"),
    ("Sadar Bazaar",           28.6620,  77.2050, "Central Delhi",  "Commercial"),
    ("Patel Nagar",            28.6580,  77.1700, "Central Delhi",  "Residential"),
    ("Rajinder Nagar",         28.6490,  77.1840, "Central Delhi",  "Residential"),
    ("Naraina",                28.6280,  77.1510, "West Delhi",     "Industrial"),
    ("Moti Nagar",             28.6600,  77.1510, "West Delhi",     "Residential"),
    ("Kirti Nagar",            28.6560,  77.1410, "West Delhi",     "Residential"),
    ("Punjabi Bagh",           28.6680,  77.1320, "West Delhi",     "Residential"),
    ("Paschim Vihar",          28.6830,  77.0980, "West Delhi",     "Residential"),
    ("Shalimar Bagh",          28.7160,  77.1590, "North West Delhi","Residential"),
    ("Ashok Vihar",            28.6990,  77.1750, "North West Delhi","Residential"),
    ("Wazirpur",               28.7010,  77.1630, "North West Delhi","Industrial"),
    ("Azadpur",                28.7200,  77.1850, "North Delhi",    "Commercial"),
    ("Mukherjee Nagar",        28.7060,  77.2090, "North Delhi",    "Commercial"),
    ("GTB Nagar",              28.7010,  77.2020, "North Delhi",    "Residential"),
    ("Kamla Nagar",            28.6870,  77.2060, "North Delhi",    "Commercial"),
    ("Kashmere Gate",          28.6680,  77.2280, "North Delhi",    "Commercial"),
    ("Daryaganj",              28.6440,  77.2440, "Central Delhi",  "Commercial"),
    ("Jangpura",               28.5880,  77.2460, "South Delhi",    "Residential"),
    ("Defence Colony",         28.5718,  77.2331, "South Delhi",    "Residential"),
    ("South Extension",        28.5680,  77.2230, "South Delhi",    "Commercial"),
    ("Green Park",             28.5580,  77.2070, "South Delhi",    "Residential"),
    ("Hauz Khas",              28.5494,  77.2001, "South Delhi",    "Commercial"),
    ("Malviya Nagar",          28.5293,  77.1980, "South Delhi",    "Residential"),
    ("Mehrauli",               28.5245,  77.1868, "South West Delhi","Residential"),
    ("Vasant Vihar",           28.5668,  77.1606, "South West Delhi","Residential"),
    ("Munirka",                28.5603,  77.1725, "South West Delhi","Residential"),
    ("R K Puram",              28.5681,  77.1780, "South West Delhi","Residential"),
    ("Palam",                  28.5983,  77.0742, "South West Delhi","Residential"),
    ("Mahipalpur",             28.5447,  77.1169, "South West Delhi","Residential"),
    ("Kapashera",              28.5105,  77.0817, "South West Delhi","Industrial"),
    ("Najafgarh",              28.6092,  76.9794, "South West Delhi","Residential"),
    ("Badarpur",               28.5021,  77.2912, "South Delhi",    "Residential"),
    ("Okhla",                  28.5350,  77.2760, "South Delhi",    "Industrial"),
    ("Jasola",                 28.5437,  77.2913, "South Delhi",    "Residential"),
    ("Kalkaji",                28.5310,  77.2590, "South Delhi",    "Residential"),
    ("Govindpuri",             28.5211,  77.2636, "South Delhi",    "Residential"),
    ("Tughlakabad",            28.5040,  77.2520, "South Delhi",    "Residential"),
    ("Sangam Vihar",           28.5083,  77.2286, "South Delhi",    "Residential"),
]

def create_zones_dataframe():
    df = pd.DataFrame(DELHI_ZONES, columns=[
        'zone_name', 'lat', 'lng', 'district', 'zone_type'
    ])
    df['zone_id'] = [f'DL_{str(i+1).zfill(3)}' for i in range(len(df))]
    print(f"✅ Created {len(df)} Delhi zones")
    return df

if __name__ == "__main__":
    df = create_zones_dataframe()
    df.to_csv('delhi_zones.csv', index=False)
    print(df.head())
    print(f"\nDistricts covered: {df['district'].nunique()}")
    print(f"Zone types: {df['zone_type'].value_counts().to_dict()}")
