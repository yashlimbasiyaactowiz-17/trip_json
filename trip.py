import json
import re
import mysql.connector
from typing import List, Dict, Any
from pydantic import BaseModel


class finalhotelmodel(BaseModel):
    basic_information: Dict[str, Any]
    policy_information: Dict[str, Any]
    location_information: Dict[str, Any]
    room_details: List[Dict[str, Any]]
    services_and_amenities: Dict[str, Any]
    reviews_information: Dict[str, Any]
    recommendations: Dict[str, Any]


# this is for loading main raw file read binary data
with open("trip_hotel.json", "rb") as file:
    raw_file_data = json.loads(file.read().decode(errors="ignore"))

cleaned_string_data = raw_file_data[1].replace("Jc:", "", 1)
main_hotel_data = json.loads(cleaned_string_data)[3]

hotel_detail = main_hotel_data.get("hotelDetailResponse", {})
seo_data = main_hotel_data.get("seoSSRData", {})

hotel_base = hotel_detail.get("hotelBaseInfo", {})
hotel_position = hotel_detail.get("hotelPositionInfo", {})
hotel_policy = hotel_detail.get("hotelPolicyInfo", {})
hotel_description = hotel_detail.get("hotelDescriptionInfo", {})

# basic info
basic_information = {
    "hotel_name": (hotel_base.get("hotelNames") or [None])[0],
    "hotel_id": main_hotel_data.get("ssrHotelRoomListRequest", {}).get("search", {}).get("hotelId"),
    "city": hotel_base.get("cityName"),
    "state": hotel_base.get("provinceName"),
    "country": hotel_base.get("countryName"),
    "description": hotel_description.get("description")
}

# policy
check_data = hotel_policy.get("checkInAndOut", {}).get("content", [])
policy_information = {
    "check_in": check_data[0].get("description") if len(check_data) > 0 else None,
    "check_out": check_data[1].get("description") if len(check_data) > 1 else None
}

# services
services_and_amenities = {}
facilities = hotel_detail.get("hotelFacilityPopV2", {}).get("hotelFacility", [])
for facility in facilities:
    title = facility.get("title")
    items = []
    for category in facility.get("categoryList", []):
        for sub in category.get("list", []):
            desc = sub.get("facilityDesc")
            if desc:
                items.append(desc)
    services_and_amenities[title] = items

# rooms
room_details = []
room_list = main_hotel_data.get("hotelCommentResponse", {}).get("commentStaticInfo", {}).get("roomList", [])
room_map = seo_data.get("seoHotelRooms", {}).get("physicRoomMap", {})

for room in room_list:
    room_id = room.get("id")
    room_data = room_map.get(str(room_id), {})
    images = [p.get("url") for p in room_data.get("pictureInfo", []) if p.get("url")]

    room_details.append({
        "room_id": room_id,
        "room_name": room.get("name"),
        "room_images": images
    })

final_data = {
    "basic_information": basic_information,
    "policy_information": policy_information,
    "room_details": room_details,
    "services_and_amenities": services_and_amenities
}

validated = finalhotelmodel(
    basic_information=basic_information,
    policy_information=policy_information,
    location_information={},
    room_details=room_details,
    services_and_amenities=services_and_amenities,
    reviews_information={},
    recommendations={}
)

# dump json
with open("final_cleaned.json", "w", encoding="utf-8") as f:
    json.dump(validated.model_dump(), f, indent=4, ensure_ascii=False)

# database connection and insertion
conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="actowiz"
)

cursor = conn.cursor()

cursor.execute("CREATE DATABASE IF NOT EXISTS hotel_db")
cursor.execute("USE hotel_db")

#  hotel_info
cursor.execute("""
CREATE TABLE IF NOT EXISTS hotel_info (
    hotel_id VARCHAR(100) PRIMARY KEY,
    hotel_name VARCHAR(255),
    city VARCHAR(100),
    state VARCHAR(100),
    country VARCHAR(100),
    description TEXT,
    check_in VARCHAR(100),
    check_out VARCHAR(100)
)
""")

#  hotel_room_details
cursor.execute("""
CREATE TABLE IF NOT EXISTS hotel_room_details (
    id INT PRIMARY KEY AUTO_INCREMENT,
    hotel_id VARCHAR(100),
    room_id VARCHAR(100),
    room_name VARCHAR(255),
    room_images JSON,
    FOREIGN KEY (hotel_id) REFERENCES hotel_info(hotel_id)
    ON DELETE CASCADE
)
""")

#  hotel_facility
cursor.execute("""
CREATE TABLE IF NOT EXISTS hotel_facility (
    id INT PRIMARY KEY AUTO_INCREMENT,
    hotel_id VARCHAR(100),
    category_title VARCHAR(255),
    facilities JSON,
    FOREIGN KEY (hotel_id) REFERENCES hotel_info(hotel_id)
    ON DELETE CASCADE
)
""")

# insert hotel_info
cursor.execute("""
INSERT INTO hotel_info
(hotel_id, hotel_name, city, state, country, description, check_in, check_out)
VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
ON DUPLICATE KEY UPDATE
hotel_name=VALUES(hotel_name),
city=VALUES(city),
state=VALUES(state),
country=VALUES(country),
description=VALUES(description),
check_in=VALUES(check_in),
check_out=VALUES(check_out)
""", (
    basic_information["hotel_id"],
    basic_information["hotel_name"],
    basic_information["city"],
    basic_information["state"],
    basic_information["country"],
    basic_information["description"],
    policy_information["check_in"],
    policy_information["check_out"]
))

# insert rooms
for room in room_details:
    cursor.execute("""
    INSERT INTO hotel_room_details
    (hotel_id, room_id, room_name, room_images)
    VALUES (%s,%s,%s,%s)
    """, (
        basic_information["hotel_id"],
        room["room_id"],
        room["room_name"],
        json.dumps(room["room_images"])
    ))

# insert facilities
for category, items in services_and_amenities.items():
    cursor.execute("""
    INSERT INTO hotel_facility
    (hotel_id, category_title, facilities)
    VALUES (%s,%s,%s)
    """, (
        basic_information["hotel_id"],
        category,
        json.dumps(items)
    ))

conn.commit()
cursor.close()
conn.close()

print("Data Inserted Successfully")