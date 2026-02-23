import json
import re
from typing import List, Optional, Dict,Any
from pydantic import BaseModel

class finalhotelmodel(BaseModel):
    basic_information: Dict[str, str]
    policy_information: Dict[str, Any]
    location_information : Dict[str, Any]
    room_details : List[Dict[str, Any]]
    services_and_amenities : Dict[str, Any]
    reviews_information : Dict[str, Any]
    recommendations : Dict[str, Any]


# this is for loading main raw file read binary data
def load_main_file(file_path):
    with open(file_path, "rb") as file:
        return json.loads(file.read().decode())

def main_trip(hotel_raw_data):

    final_hotel_dictionary = {}

# paths
    hotel_detail = hotel_raw_data.get("hotelDetailResponse", {})
    seo_data = hotel_raw_data.get("seoSSRData", {})

    hotel_base = hotel_detail.get("hotelBaseInfo", {})
    hotel_position = hotel_detail.get("hotelPositionInfo", {})
    hotel_policy = hotel_detail.get("hotelPolicyInfo", {})
    hotel_description = hotel_detail.get("hotelDescriptionInfo", {})
    hotel_comment = hotel_detail.get("hotelComment", {}).get("comment", {})

# service and amiites
    services_and_amenities = {}

    facilities = hotel_detail.get("hotelFacilityPopV2", {}).get("hotelFacility", [])
    for facility in facilities:
        title = facility.get("title")
        if not title:
            continue

        items = []
        categories = facility.get("categoryList", [])
        for category in categories:
            sub_list = category.get("list", [])
            for sub in sub_list:
                desc = sub.get("facilityDesc")
                if desc:
                    clean = desc.split("Additional charge")[0].strip()
                    if clean:
                        items.append(clean)

        if items:
            services_and_amenities[title] = items
        else:
            services_and_amenities[title] = [None]

# recomendation
    recommendations = {}
    footer = seo_data.get("seoFooterModule", {})
    footer_title = footer.get("title")

    if footer_title:
        recommendations[footer_title] = {}
        footer_items = footer.get("footerItem", [])

        if footer_items:
            section = footer_items[0]
            section_name = section.get("title", "").replace(" ", "_")
            recommendations[footer_title][section_name] = []

            link_items = section.get("linkItem", [])
            for item in link_items:
                hotel_obj = {
                    "hotel_name": item.get("text"),
                    "hotel_url": item.get("url")
                }
                recommendations[footer_title][section_name].append(hotel_obj)

# room detaisy
    room_details = []

    room_list = hotel_raw_data.get("hotelCommentResponse", {}).get("commentStaticInfo", {}).get("roomList", [])
    room_map = seo_data.get("seoHotelRooms", {}).get("physicRoomMap", {})

    for room in room_list:
        room_id = room.get("id")
        if not room_id:
            continue

        room_data = room_map.get(str(room_id), {})

        images = []
        picture_info = room_data.get("pictureInfo", [])
        for p in picture_info:
            url = p.get("url")
            if url:
                images.append(url)

        facilities = []

        base_facility = room_data.get("baseFacilityInfo", [])
        for f in base_facility:
            title = f.get("title")
            if title:
                facilities.append(title)

        bed_title = room_data.get("bedInfo", {}).get("title")
        if bed_title:
            facilities.append(bed_title)

        new_facility = room_data.get("newFacilityList", [])
        for f in new_facility:
            title = f.get("title")
            if title:
                facilities.append(title)

        room_obj = {
            "room_id": room_id,
            "room_name": room.get("name"),
            "room_images": images,
            "room_facilities": facilities
        }

        room_details.append(room_obj)

#location
    full_address = hotel_position.get("address", "")

    pincode = None
    if full_address:
        match = re.search(r"\d{6}", full_address)
        if match:
            pincode = match.group()

    nearby_places = []
    place_list = hotel_position.get("placeInfo", {}).get("wholePoiInfoList", [])
    for p in place_list:
        place_obj = {
            "place_name": p.get("poiName"),
            "distance": p.get("distance"),
            "distance_type": p.get("distType")
        }
        nearby_places.append(place_obj)

    location_information = {
        "hotel_name": (hotel_base.get("hotelNames") or [None])[0],
        "hotel_id": hotel_raw_data.get("ssrHotelRoomListRequest", {}).get("search", {}).get("hotelId"),
        "address_details": {
            "Full_Address": full_address,
            "City": hotel_base.get("cityName"),
            "State": hotel_base.get("provinceName"),
            "Country": hotel_base.get("countryName"),
            "Pincode": pincode
        },
        "nearby_places": nearby_places
    }

# review part
    customer_reviews = []
    positive_reviews = hotel_comment.get("positiveDirection", [])
    for r in positive_reviews:
        review_obj = {
            "guest_name": r.get("userInfo", {}).get("nickName"),
            "guest_id": r.get("id"),
            "review_comment": r.get("content"),
            "guest_profile_image": r.get("userInfo", {}).get("headPictureUrl")
        }
        customer_reviews.append(review_obj)

    rating_details = []
    score_details = hotel_comment.get("scoreDetail", [])
    for r in score_details:
        rating_obj = {
            "rating_category": r.get("showName"),
            "rating_score": r.get("showScore")
        }
        rating_details.append(rating_obj)

    reviews_information = {
        "customer_reviews": customer_reviews,
        "rating_details": rating_details
    }

# basic name , id , policy
    labels = hotel_description.get("lables", [])
    phones = hotel_description.get("tels", [])

    number_of_rooms = None
    open_year = None

    if len(labels) > 1:
        number_of_rooms = labels[1][17:21]
    if len(labels) > 0:
        open_year = labels[0][8:13]

    phone_number = None
    if phones:
        phone_number = phones[0].get("show")

    basic_information = {
        "number_of_rooms": number_of_rooms,
        "open_year": open_year,
        "phone_number": phone_number,
        "description": hotel_description.get("description")
    }

    check_data = hotel_policy.get("checkInAndOut", {}).get("content", [])
    breakfast_data = hotel_policy.get("breakfast", {}).get("content", [])

    check_in_time = None
    check_out_time = None
    front_desk_hours = None

    if len(check_data) > 0:
        check_in_time = check_data[0].get("description")
    if len(check_data) > 1:
        check_out_time = check_data[1].get("description")
    if len(check_data) > 2:
        front_desk_hours = check_data[2].get("description")

    breakfast_timing = None
    breakfast_price = None

    if len(breakfast_data) > 1:
        breakfast_timing = breakfast_data[1].get("description")

    if len(breakfast_data) > 2:
        tab = breakfast_data[2].get("tab", {})
        table_items = tab.get("tableItems", [])
        if table_items:
            table_details = table_items[0].get("tableDetails", [])
            if len(table_details) > 1:
                content = table_details[1].get("content", "")
                breakfast_price = content[9:]

    policy_information = {
        "check_in_time": check_in_time,
        "check_out_time": check_out_time,
        "front_desk_hours": front_desk_hours,
        "breakfast_details": {
            "breakfast_timing": breakfast_timing,
            "breakfast_price": breakfast_price
        }
    }

# final code main dict
    final_hotel_dictionary["basic_information"] = basic_information
    final_hotel_dictionary["policy_information"] = policy_information
    final_hotel_dictionary["location_information"] = location_information
    final_hotel_dictionary["room_details"] = room_details
    final_hotel_dictionary["services_and_amenities"] = services_and_amenities
    final_hotel_dictionary["reviews_information"] = reviews_information
    final_hotel_dictionary["recommendations"] = recommendations

    return final_hotel_dictionary


# this is for load and cleaning data
file_name = "trip_hotel.json"

raw_file_data = load_main_file(file_name)
cleaned_string_data = raw_file_data[1].replace("Jc:", "", 1)
main_hotel_data = json.loads(cleaned_string_data)[3]

# this is load cleaning data and dump
def convert_json_dump(result_data):
    with open("sceleton.json", "wb") as output_file:
        output_file.write(json.dumps(result_data, indent=4, ensure_ascii=False).encode())

parsed_result = main_trip(main_hotel_data)
validated=finalhotelmodel(**parsed_result)
convert_json_dump(validated.model_dump())
# convert_json_dump(parsed_result)

print(parsed_result)