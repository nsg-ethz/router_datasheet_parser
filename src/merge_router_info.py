from tqdm import tqdm
from collections import OrderedDict
from load_file import *


def merge_dicts(dict1, dict2):
    """
    Merge two dictionaries into one. Specifically in the case of two same keys:
    1. If the two values are also the same: It even verify our confidence of this value is more than perfect.
    2. If the one of the values is null: Overwrite null with the non-null value.
    
    Parameters:
        dict1:  The first dictionary
        dict2:  The second dictionary
    """
    for key, value in dict2.items():
        # If the key exists in both dictionaries
        if key in dict1:
            if isinstance(value, dict) and isinstance(dict1[key], dict):
                merge_dicts(dict1[key], value)
            # If both values are non-null and different, combine them as "value 1 and value 2"
            elif value and dict1[key] and value != dict1[key]:
                dict1[key] = f"{dict1[key]} and {value}"
            # If one of the values is null, use the non-null value
            elif not dict1[key]:
                dict1[key] = value
        else:
            # If key only exists in dict2, add it to dict1
            dict1[key] = value
    
    return dict1


def organize_dicts(data):
    """
    Organize the dictionary into the format that we want
    
    Parameters:
        data:   The dictionary data waiting to be organized
    
    Returns:
        organized_data: The organized dictionary data in the format that we want
    """
    organized_data = OrderedDict([
        ("manufacturer", data["manufacturer"]),
        ("series", data["series"]),
        ("model", data["model"]),
        ("slug", data["slug"]),
        ("part_number", data["part_number"]),
        ("u_height", data["u_height"]),
        ("router_type", data["router_type"]),
        ("datasheet_url", data["datasheet_url"]),
        ("datasheet_pdf", data["datasheet_pdf"]),
        ("release_date", data["release_date"]),
        ("end_of_sale", data["end_of_sale"]),
        ("end_of_support", data["end_of_support"]),
        ("max_throughput", data["max_throughput"]),
        ("max_power_draw", data["max_power_draw"]),
        ("typical_power_draw", data["typical_power_draw"]),
        ("is_poe_capable", data["is_poe_capable"]),
        ("max_poe_draw", data["max_poe_draw"]),
        ("psu", data["psu"]),
    ])

    return dict(organized_data)


def all_files_exist(files):
    """
    Check if all files in the list exist.

    Parameters:
        files (list): List of file paths to check.

    Returns:
        bool: True if all files exist, False if any file is missing.
    """
    return all(os.path.isfile(file) for file in files)


if __name__ == "__main__":

    result_dir = "../result/cisco/"
    routers_without_url = "../result/routers_without_url.csv"
    router_series = [\
            "me_3600x_series_ethernet_access_switches", 
            "cisco_business_350_series_managed_switches", \
            "nexus_2000_series_fabric_extenders", \
            "aironet_2700_series_access_points", \
            "cisco_350_series_managed_switches", \
            "aironet_1240_series", \
            "cisco_300_series_managed_switches", \
            "catalyst_2960_plus_series_switches", \
            "500_series_wpan_industrial_routers", \
            "cisco_2500_series_access_servers", \
            "cisco_asa_5500_x_series_firewalls", \
            "catalyst_3650_series_switches", \
            "asa_5500_x_series_next_generation_firewalls", \
            "small_business_rv_series_routers"
        ]

    for series_folder in tqdm(router_series):

        series_path = os.path.join(result_dir, series_folder)

        for router_name in os.listdir(series_path):

            filtered_netbox_file = series_path + "/" + router_name + "/filtered_netbox.yaml"
            general_llm_file = series_path + "/" + router_name + "/general_llm.yaml"
            date_file = series_path + "/" + router_name + "/date_llm.yaml"
            type_file = series_path + "/" + router_name + "/type_llm.yaml"

            # List of required files
            required_files = [filtered_netbox_file, general_llm_file, date_file, type_file]

            # Skip loop if any of the required files is missing
            if not all_files_exist(required_files):
                print(f"Skipping {router_name} due to missing files.")
                continue

            # Load each file
            filtered_netbox_data = load_yaml(filtered_netbox_file)
            url_llm_data = load_yaml(general_llm_file)
            date_data = load_yaml(date_file)
            type_data = load_yaml(type_file)

            # Begin to merge the data
            merged_data = {
                "manufacturer": None,
                "series": None,
                "model": None,
                "slug": None,
                "part_number": None,
                "u_height": None,
                "router_type": None,
                "datasheet_url": None,
                "datasheet_pdf": None,
                "release_date": None,
                "end_of_sale": None,
                "end_of_support": None,
                "max_throughput": None,
                "max_power_draw": None,
                "typical_power_draw": None,
                "is_poe_capable": None,
                "max_poe_draw": None,
                "psu": None,
            }
            merge_dicts(merged_data, filtered_netbox_data)
            merge_dicts(merged_data, url_llm_data)
            merge_dicts(merged_data, date_data)
            merge_dicts(merged_data, type_data)
            
            organzed_data = organize_dicts(merged_data)
            output_file = os.path.join(series_path, router_name, "merged.yaml")
            save_yaml(organzed_data, output_file)
