import os
from tqdm import tqdm
import plotly.express as px
from datetime import datetime
from load_file import *


def plot_release_date_max_throughput(release_date_max_throughput):
    
    dates = []
    throughputs = []
    router_names = []

    for router_name, (release_date, max_throughput) in release_date_max_throughput.items():
        
        date = datetime.strptime(release_date, '%Y-%m-%d')
        throughput_value = max_throughput['value']
        unit = max_throughput['unit']
        
        # Convert units to Gbps if necessary
        if unit == 'Mbps':
            throughput_value /= 1000
        elif unit == 'Kbps':
            throughput_value /= 1_000_000
        
        dates.append(date)
        throughputs.append(throughput_value)
        router_names.append(router_name)

    # Plotting
    fig = px.scatter(
        x=dates, 
        y=throughputs, 
        text=router_names, 
        labels={'x': 'Release Date', 'y': 'Max Throughput (Gbps)'},
        title='Router Max Throughput over Release Dates'
    )
    fig.update_traces(marker=dict(size=10), textposition='top center')
    fig.update_layout(xaxis=dict(type='date'), showlegend=False)
    fig.show()
    fig.write_html("router_max_throughput_over_time.html")


def plot_release_date_max_power_draw(release_date_max_power_draw):
    
    dates = []
    max_power_values = []
    router_names = []

    for router_name, (release_date, max_power_draw_data) in release_date_max_power_draw.items():
        date = datetime.strptime(release_date, '%Y-%m-%d')
        max_power_value = max_power_draw_data['value']
        unit = max_power_draw_data['unit']
        
        # Append values to respective lists
        dates.append(date)
        max_power_values.append(max_power_value)
        router_names.append(router_name)

    # Plotting
    fig = px.scatter(
        x=dates, 
        y=max_power_values, 
        text=router_names, 
        labels={'x': 'Release Date', 'y': 'Max Power Draw (W)'},
        title='Router Max Power Draw over Release Dates'
    )
    fig.update_traces(marker=dict(size=10), textposition='top center')
    fig.update_layout(xaxis=dict(type='date'), showlegend=False)
    fig.show()
    fig.write_html("router_max_power_draw_over_time.html")


def plot_release_date_sys_eff(release_date_max_throughput, release_date_max_power_draw):
    
    dates = []
    throughputs = []
    max_power_values = []
    router_names = []
    sys_eff = []

    for router_name, (release_date, max_throughput) in release_date_max_throughput.items():
        # Convert the release date
        date = datetime.strptime(release_date, '%Y-%m-%d')
        throughput_value = max_throughput['value']
        throughput_unit = max_throughput['unit']
        
        # Convert units to Gbps if necessary
        if throughput_unit == 'Mbps':
            throughput_value /= 1000
        elif throughput_unit == 'Kbps':
            throughput_value /= 1_000_000
        
        # Retrieve corresponding max power draw for the same router
        if router_name in release_date_max_power_draw:
            max_power_draw_data = release_date_max_power_draw[router_name][1]  # Extract the max power draw dictionary
            max_power_value = max_power_draw_data['value']
            
            # Calculate system efficiency
            efficiency = throughput_value / max_power_value
            sys_eff.append(efficiency)

            # Store data for plotting
            dates.append(date)
            throughputs.append(throughput_value)
            max_power_values.append(max_power_value)
            router_names.append(router_name)


    # Plotting
    fig = px.scatter(
        x=dates, 
        y=sys_eff, 
        text=router_names, 
        labels={'x': 'Release Date', 'y': 'System Efficiency'},
        title='Router System Efficiency over Release Dates'
    )
    fig.update_traces(marker=dict(size=10), textposition='top center')
    fig.update_layout(xaxis=dict(type='date'), showlegend=False)
    fig.show()
    fig.write_html("router_system_efficiency_over_time.html")


if __name__ == "__main__":

    # Currently, the code is only for Cisco
    result_dir = "../result/cisco/"

    release_date_max_throughput = {}
    release_date_max_power_draw = {}

    for series_folder in tqdm(os.listdir(result_dir)):

        # All the following code is conducted for the routers under the same series
        series_path = os.path.join(result_dir, series_folder)
                
        for router_name in os.listdir(series_path):
            
            merge_file = os.path.join(series_path, router_name, "merged.yaml")

            if os.path.exists(merge_file):
                merge_file_content = load_yaml(merge_file)
                if merge_file_content.get("release_date") is not None \
                    and merge_file_content.get("max_throughput") is not None:
                    release_date_max_throughput[merge_file_content["model"]] = [merge_file_content["release_date"]["value"], merge_file_content["max_throughput"]]
            
            if os.path.exists(merge_file):
                merge_file_content = load_yaml(merge_file)
                if merge_file_content.get("release_date") is not None \
                    and merge_file_content.get("max_power_draw") is not None:
                    release_date_max_power_draw[merge_file_content["model"]] = [merge_file_content["release_date"]["value"], merge_file_content["max_power_draw"]]
    
    # plot_release_date_max_throughput(release_date_max_throughput)
    # print("release_date_max_power_draw: ",release_date_max_power_draw)
    # plot_release_date_max_power_draw(release_date_max_power_draw)
    plot_release_date_sys_eff(release_date_max_throughput, release_date_max_power_draw)