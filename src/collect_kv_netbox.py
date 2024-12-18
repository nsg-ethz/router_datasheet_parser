import os
from tqdm import tqdm
from collections import Counter, defaultdict
from load_file import *

def count_netbox_keys(router_dir):
    """
    Collect the information of how many times of the key from the NetBox original appear.
    We do this for these purposes:
    1. The structure of each NetBox is not unified, causing that we don't know if we will miss some keys.
    2. The PSU info is stored either in power-ports or module-bays or nowhere, causing that we don't know how to count the number of psu within a router.
    
    Parameters:
        router_dir (str): The relative path of the router.

    Returns:
        dict: The key is a router feature, and the value is the number it appears in the whole directory.
        dict: The key is the nested attribute of a router feature, and the value is the number it appears in the whole directory.
    """

    key_counter = Counter()
    excluding_list = ["is_full_depth", "subdevice_role", "weight", "weight_unit", "front_image", "rear_image", "airflow", "is_powered", "interfaces"]

    # Create a defaultdict to store more specific info for 'parameter.name' fields
    specific_name_counter = defaultdict(lambda: Counter())

    files = [f for f in os.listdir(router_dir) if os.path.isfile(os.path.join(router_dir, f))]

    def process_nested_dict(content_d, parent_key=""):
        for key, value in content_d.items():
            if key in excluding_list:
                continue

            full_key = f"{parent_key}.{key}" if parent_key else key

            if isinstance(value, dict):
                process_nested_dict(value, full_key)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        process_nested_dict(item, full_key)
            else:
                if parent_key and key == 'name':
                    specific_name_counter[parent_key][value] += 1
                else:
                    key_counter[full_key] += 1

    for filename in tqdm(files):
        content = load_yaml(os.path.join(router_dir, filename))
        process_nested_dict(content)

    return key_counter, specific_name_counter


if __name__ == "__main__":

    manufacturers = ["Cisco", "Arista", "Juniper"]
    
    for manufacturer in manufacturers:

        print("Selected Manufacturer: ", manufacturer)

        router_dataset_dir = os.path.join("../dataset", manufacturer)
        key_counts, specific_name_counts = count_netbox_keys(router_dataset_dir)

        router_result_dir = os.path.join("../result", manufacturer.lower())
        os.makedirs(router_result_dir, exist_ok=True)
        netbox_keys_file = os.path.join(router_result_dir, "netbox_keys.yaml")

        # Prepare data for YAML output
        data_to_store = {**dict(key_counts), **{parent_key + ".name": dict(names) for parent_key, names in specific_name_counts.items()}}

        # Write the results to the YAML file
        save_yaml(data_to_store, netbox_keys_file)

        print(f"Results have been saved to {netbox_keys_file}")
