import os
from load_file import *

def extract_series(manufacturer_dir):

    for series_dir in os.listdir(manufacturer_dir):
        series_folder = os.path.join(manufacturer_dir, series_dir)

        for root, dirs, files in os.walk(series_folder):
                for router_dir in dirs:

                    router_path = os.path.join(series_folder, router_dir)
                    filtered_netbox_path = os.path.join(router_path, "filtered_netbox.yaml")
                    series_path = os.path.join(router_path, "series.yaml")

                    # Skip if filtered_netbox.yaml does not exist
                    if not os.path.isfile(filtered_netbox_path):
                        continue

                    # Load the filtered_netbox.yaml
                    filtered_data = load_yaml(filtered_netbox_path)

                    # Check if 'series' exists
                    if "series" in filtered_data:
                        series_data = {"series": filtered_data.pop("series")}

                        # Save the 'series' data to series.yaml
                        save_yaml(series_data, series_path)
                        print(f"Saved series.yaml for {router_dir}")

                        # Overwrite filtered_netbox.yaml without the 'series' field
                        save_yaml(filtered_data, filtered_netbox_path)
                        print(f"Updated filtered_netbox.yaml for {router_dir}")
                    else:
                        print(f"No 'series' field found in filtered_netbox.yaml for {router_dir}")


if __name__ == "__main__":
    # Path to the directory containing all router folders
    manufacturer_dir = "../result/cisco/"
    extract_series(manufacturer_dir)