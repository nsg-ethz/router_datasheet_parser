import os
import plotly.express as px
import pandas as pd
from load_file import *


def plot_release_date_max_throughput(manufacturer, df):
    """
    Plot the scatter figure to show the relationship between release_date and max_throughput.

    Parameters:
        manufacturer:   The manufacturer of a router.
        df:             The df containing the routers max_throughput and release_date.
    
    Returns:
        The html and png files of the figure.
    """
    df['release_date'] = pd.to_datetime(df['release_date'])
    df_filtered = df.dropna(subset=['max_throughput', 'release_date'])

    print("max throughput and the release date: ", df_filtered.shape[0])

    fig = px.scatter(
        df_filtered,
        x='release_date',
        y='max_throughput',
        # color='router_type',
        title='Max Throughput Over Release Dates by Router Series',
        labels={'release_date': 'Release Date', 'max_throughput': 'Max Throughput (Gbps)'},
        hover_name='router_name',
        # category_orders={'router_type': ['access', 'aggregation', 'other']}
    )

    os.makedirs("../fig/" + manufacturer, exist_ok=True)
    fig.write_html(f"../fig/{manufacturer}/max_throughput_by_release_date_{manufacturer}.html")
    fig.write_image(f"../fig/{manufacturer}/max_throughput_by_release_date_{manufacturer}.png")


def plot_release_date_max_power_draw(manufacturer, df):
    """
    Plot the scatter figure to show the relationship between release_date and max_power_draw.

    Parameters:
        manufacturer:   The manufacturer of a router.
        df:             The df containing the routers max_power_draw and release_date.
    
    Returns:
        The html and png files of the figure.
    """
    df['release_date'] = pd.to_datetime(df['release_date'])
    df_filtered = df.dropna(subset=['max_power_draw', 'release_date'])

    print("max power draw and the release date: ", df_filtered.shape[0])

    fig = px.scatter(
        df_filtered,
        x='release_date',
        y='max_power_draw',
        # color='router_type',
        title='Max Power Draw Over Release Dates by Router Series',
        labels={'release_date': 'Release Date', 'max_power_draw': 'Max Power Draw (W)'},
        hover_name='router_name',
        # category_orders={'router_type': ['access', 'aggregation', 'other']}
    )

    os.makedirs("../fig/" + manufacturer, exist_ok=True)
    fig.write_html(f"../fig/{manufacturer}/max_power_draw_by_release_date_{manufacturer}.html")
    fig.write_image(f"../fig/{manufacturer}/max_power_draw_by_release_date_{manufacturer}.png")


def plot_release_date_power_efficiency(manufacturer, df):
    """
    Plot the scatter figure to show the relationship between release_date and power_efficiency.
    The power effiency is defined as max_power_draw/max_throughput

    Parameters:
        manufacturer:   The manufacturer of a router.
        df:             The df containing the routers max_power_draw, max_throughput and release_date.
    
    Returns:
        The html and png files of the figure.
    """

    df_filtered = df.dropna(subset=['max_power_draw', 'max_throughput', 'release_date'])

    df_filtered['power_efficiency'] = df_filtered['max_power_draw'] / df_filtered['max_throughput']
    
    # Convert the release date to datetime if it's not already
    df_filtered['release_date'] = pd.to_datetime(df_filtered['release_date'])

    fig = px.scatter(
        df_filtered,
        x='release_date',
        y='power_efficiency',
        # color='router_type',
        title='Power Efficiency (Max Power Draw / Max Throughput) Over Release Dates',
        labels={'release_date': 'Release Date', 'power_efficiency': 'Power Efficiency (W/Gbps)'},
        hover_name='router_name',
        # category_orders={'router_type': ['access', 'aggregation', 'other']}
    )

    os.makedirs("../fig/" + manufacturer, exist_ok=True)
    fig.write_html(f"../fig/{manufacturer}/power_efficiency_by_release_date_{manufacturer}.html")
    fig.write_image(f"../fig/{manufacturer}/power_efficiency_by_release_date_{manufacturer}.png")


def plot_throughput_power_draw(manufacturer, df):
    """
    Plot the scatter figure to show the relationship between max_throughput and max_power_draw.

    Parameters:
        manufacturer:   The manufacturer of a router.
        df:             The df containing the routers max_power_draw and max_throughput.
    
    Returns:
        The html and png files of the figure.
    """
    df_filtered = df.dropna(subset=['max_power_draw', 'max_throughput'])

    print("max throughput and max power draw: ", df_filtered.shape[0])

    fig = px.scatter(
        df_filtered,
        x='max_throughput',
        y='max_power_draw',
        title='Relationship between Max Throughput and Max Power Draw',
        labels={'max_throughput': 'Max Throughput', 'max_power_draw': 'Max Power Draw (W)'},
        # color='router_type',
        hover_name='router_name',
        # category_orders={'router_type': ['access', 'aggregation', 'other']}
    )

    # Save the plot as an image
    os.makedirs("../fig/" + manufacturer, exist_ok=True)
    fig.write_html(f"../fig/{manufacturer}/throughput_power_{manufacturer}.html")
    fig.write_image(f"../fig/{manufacturer}/throughput_power_{manufacturer}.png")


def convert_throughput_unit(value, unit):

    if unit.lower() == "mbps":
        value /= 1000
    elif unit.lower() == "kbps":
        value /= 1000000
    elif unit.lower() == "tbps":
        value *= 1000

    return value


def convert_power_unit(value, unit):

    if unit.lower() == "kw":
        value *= 1000
    elif unit.lower() == "btu/hr":
        value *= 0.293071
    
    return value


if __name__ == "__main__":

    result_dir = "../result/"

    for manufacturer in os.listdir(result_dir):
        manufacturer_dir = os.path.join(result_dir, manufacturer)

        if manufacturer == "cisco":
        
            df = pd.DataFrame(columns=["router_name", "max_throughput", "max_power_draw", "release_date"])

            for series_dir in os.listdir(manufacturer_dir):

                series_folder = os.path.join(manufacturer_dir, series_dir)

                for root, dirs, files in os.walk(series_folder):

                    for router_dir in dirs:
                        
                        if os.path.exists(os.path.join(series_folder, router_dir, "merged.yaml")):
                            
                            merged_content = load_yaml(os.path.join(series_folder, router_dir, "merged.yaml"))
                            router_series = merged_content["series"]
                            router_name = merged_content["model"]
                            release_date = merged_content["release_date"]
                            # router_type = merged_content.get("router_type")
                            max_throughput = merged_content.get("max_throughput")
                            max_power_draw = merged_content.get("max_power_draw")
                            # router_type_value = router_type.get("value") if router_type else None
                            # if router_type_value not in ["access", "aggregation"]:
                            #     router_type_value = "other"
                            max_throughput_value = max_throughput.get("value") if max_throughput else None
                            max_power_draw_value = max_power_draw.get("value") if max_power_draw else None
                            
                            # Unify the throughput unit to Gbps
                            if (max_throughput_value) and (max_throughput.get("unit").lower() != "gbps"):
                                max_throughput_value = convert_throughput_unit(max_throughput_value, max_throughput.get("unit"))
                            
                            # Unify the power unit to W
                            if (max_power_draw_value) and (max_power_draw.get("unit").lower() != "w"):
                                max_power_draw_value = convert_power_unit(max_power_draw_value, max_power_draw.get("unit"))
                            
                            new_row = pd.DataFrame({
                                # "router_type": [router_type_value],
                                "router_name": [router_name],
                                "max_throughput": [max_throughput_value],
                                "max_power_draw": [max_power_draw_value],
                                "release_date": [release_date]
                            })

                            df = pd.concat([df, new_row], ignore_index=True)

            plot_throughput_power_draw(manufacturer,df)
            plot_release_date_max_throughput(manufacturer, df)
            plot_release_date_max_power_draw(manufacturer, df)
            plot_release_date_power_efficiency(manufacturer, df)

        # There are no release_date for Arista or Juniper
        else:

            df = pd.DataFrame(columns=["router_name", "max_throughput", "max_power_draw"])

            for root, dirs, files in os.walk(manufacturer_dir):

                for router_dir in dirs:
                    
                    if os.path.exists(os.path.join(manufacturer_dir, router_dir, "merged.yaml")):
                        
                        merged_content = load_yaml(os.path.join(manufacturer_dir, router_dir, "merged.yaml"))
                        router_series = merged_content["series"]
                        router_name = merged_content["model"]
                        # release_date = merged_content["release_date"]
                        # router_type = merged_content.get("router_type")
                        max_throughput = merged_content.get("max_throughput")
                        max_power_draw = merged_content.get("max_power_draw")
                        # router_type_value = router_type.get("value") if router_type else None
                        # if router_type_value not in ["access", "aggregation"]:
                        #     router_type_value = "other"
                        max_throughput_value = max_throughput.get("value") if max_throughput else None
                        max_power_draw_value = max_power_draw.get("value") if max_power_draw else None
                        
                        # Unify the throughput unit to Gbps
                        if (max_throughput_value) and (max_throughput.get("unit").lower() != "gbps"):
                            max_throughput_value = convert_throughput_unit(max_throughput_value, max_throughput.get("unit"))
                        
                        # Unify the power unit to W
                        if (max_power_draw_value) and (max_power_draw.get("unit").lower() != "w"):
                            max_power_draw_value = convert_power_unit(max_power_draw_value, max_power_draw.get("unit"))
                        
                        new_row = pd.DataFrame({
                            # "router_type": [router_type_value],
                            "router_name": [router_name],
                            "max_throughput": [max_throughput_value],
                            "max_power_draw": [max_power_draw_value]
                        })

                        df = pd.concat([df, new_row], ignore_index=True)

            plot_throughput_power_draw(manufacturer, df)
