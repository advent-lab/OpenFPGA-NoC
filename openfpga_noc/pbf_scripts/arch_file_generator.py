import os
import sys
import shutil
import time
from datetime import timedelta
import shlex
import argparse
from configparser import ConfigParser, ExtendedInterpolation
import logging
import glob
import subprocess
import threading
import csv
from string import Template
import pprint
from importlib import util
from collections import OrderedDict
from lxml import etree as ET


if util.find_spec("coloredlogs"):
    import coloredlogs
if util.find_spec("humanize"):
    import humanize


def parse_size(size_str):
    size_str = size_str.strip("[]")
    if ":" in size_str:
        start, end = map(int, size_str.split(":"))
        return abs(start - end) + 1
    return 1

def indent_xml(elem, level=0):
    i = "\n" + level * "   "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "   "
        for subelem in elem:
            indent_xml(subelem, level + 1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if not elem.tail or not elem.tail.strip():
            elem.tail = i

def add_vpr_model(top, 
                #   port_dict, 
                # directional_ports,
                # north_input_ports, north_output_ports, east_input_ports, east_output_ports, south_input_ports, south_output_ports, west_input_ports, west_output_ports,
                 core_input_ports, core_output_ports, clock_reset_ports,
                  has_clock, clock_port, vpr_arch_file, root, tree):
    # Create the new <model> tag
    new_model = ET.Element('model', {'name': top})
    input_ports = ET.SubElement(new_model, 'input_ports')
    output_ports = ET.SubElement(new_model, 'output_ports')

    # all core outputs as string
    #
    output_ports_string = ""
    for port, size in core_output_ports:
        output_ports_string += f"{port} "

    # remove space in beginning and end
    output_ports_string = output_ports_string.strip()


    ## TODO: Add combinational and sequential type of ports definition in models

    input_ports.append(ET.Comment(' Clock and reset ports'))
    for port in clock_reset_ports:
        if port == clock_port:
            input_ports.append(ET.Element('port', {'name': port, 'is_clock': '1'}))
        else:
            input_ports.append(ET.Element('port', {'name': port, 'clock': clock_port, 'combinational_sink_ports': output_ports_string}))
    input_ports.append(ET.Comment(' Core input ports'))
    for port, size in core_input_ports:
        input_ports.append(ET.Element('port', {'name': port, 'clock': clock_port, 'combinational_sink_ports': output_ports_string}))
    input_ports.append(ET.Comment(' Model does not have router-to-router ports'))

    for port, size in core_output_ports:
        output_ports.append(ET.Element('port', {'name': port, 'clock': clock_port}))
    output_ports.append(ET.Comment(' Model does not have router-to-router ports'))

    # Indent 
    indent_xml(new_model, level=2)

    # Find the <models> tag
    models_element = root.find('.//models')

    models_element.append(new_model)

    tree.write(vpr_arch_file)
    # print(f" ---------- Added model '{top}' in VPR arch file at $arch_dir/vpr_arch.xml")


def add_vpr_tile(top, 
                #  port_dict,
                directional_in_ports, directional_out_ports,
                 north_input_ports, north_output_ports, east_input_ports, east_output_ports, south_input_ports, south_output_ports, west_input_ports, west_output_ports, core_input_ports, core_output_ports, clock_reset_ports, 
                 tile_size,
                 has_clock, clock_port, vpr_arch_file, root, tree):
    interface = 'axis'
    # Create the new <tile> tag
    new_tile = ET.Element('tile', {'name': f'{top}_tile', 'width': f'{tile_size[0]}', 'height': f'{tile_size[1]}'})
    sub_tile = ET.SubElement(new_tile, 'sub_tile', {'name': f'{top}_tile'})
    equivalent_sites = ET.SubElement(sub_tile, 'equivalent_sites')
    ET.SubElement(equivalent_sites, 'site', {'pb_type': f'{top}_tile'})

    tile_size_x = tile_size[0] -1
    tile_size_y = tile_size[1] -1
    # First collect all ports by direction to use for both fc_override and pinlocations
    # north_input_ports = []
    # north_output_ports = []
    # east_input_ports = []
    # east_output_ports = []
    # south_input_ports = []
    # south_output_ports = []
    # west_input_ports = []
    # west_output_ports = []
    # core_input_ports = []
    # core_output_ports = []
    # clock_reset_ports = []

    # Group ports by direction (based on naming conventions)
    # for input_port in port_dict[top]["inputs"]:
    #     for name, size in input_port.items():
    #         if name == clock_port or 'clk' in name.lower() or 'rst' in name.lower() or 'reset' in name.lower():
    #             clock_reset_ports.append(name)
    #         elif 'top' in name.lower() or 'north' in name.lower():
    #             north_input_ports.append((name, size))
    #         elif 'right' in name.lower() or 'east' in name.lower():
    #             east_input_ports.append((name, size))
    #         elif 'bottom' in name.lower() or 'south' in name.lower():
    #             south_input_ports.append((name, size))
    #         elif 'left' in name.lower() or 'west' in name.lower():
    #             west_input_ports.append((name, size))
    #         else:
    #             core_input_ports.append((name, size))

    # for output_port in port_dict[top]["outputs"]:
    #     for name, size in output_port.items():
    #         if 'top' in name.lower() or 'north' in name.lower():
    #             north_output_ports.append((name, size))
    #         elif 'right' in name.lower() or 'east' in name.lower():
    #             east_output_ports.append((name, size))
    #         elif 'bottom' in name.lower() or 'south' in name.lower():
    #             south_output_ports.append((name, size))
    #         elif 'left' in name.lower() or 'west' in name.lower():
    #             west_output_ports.append((name, size))
    #         else:
    #             core_output_ports.append((name, size))


    # Declare all ports
    # for input_port in port_dict[top]["inputs"]:
    #     for name, size in input_port.items():
    #         if name == clock_port:
    #             ET.SubElement(sub_tile, 'clock', {'name': clock_port, 'num_pins': '1'})
    #         else:
    #             ET.SubElement(sub_tile, 'input', {'name': name, 'num_pins': f'{size}'})
    # for output_port in port_dict[top]["outputs"]:
    #     for name, size in output_port.items():
    #         ET.SubElement(sub_tile, 'output', {'name': name, 'num_pins': f'{size}'})
    sub_tile.append(ET.Comment(' Clock and reset ports'))
    for port in clock_reset_ports:
        if port == clock_port:
            ET.SubElement(sub_tile, 'clock', {'name': clock_port, 'num_pins': '1'})
        else:
            ET.SubElement(sub_tile, 'input', {'name': port, 'num_pins': '1'})
    sub_tile.append(ET.Comment(' Core input ports'))
    for port, size in core_input_ports:
        ET.SubElement(sub_tile, 'input', {'name': port, 'num_pins': f'{size}'})
    sub_tile.append(ET.Comment(' Core output ports'))
    for port, size in core_output_ports:
        ET.SubElement(sub_tile, 'output', {'name': port, 'num_pins': f'{size}'})
    sub_tile.append(ET.Comment(' Router-to-router ports'))
    # if directional_ports:
        #  directional ports is a set of two lists
    # check if these lists are populated
    if directional_in_ports and directional_out_ports:
        sub_tile.append(ET.Comment(' Input directional ports'))
        for port, size in directional_in_ports:
            ET.SubElement(sub_tile, 'input', {'name': port, 'num_pins': f'{size}'})
        sub_tile.append(ET.Comment(' Output directional ports'))
        for port, size in directional_out_ports:
            ET.SubElement(sub_tile, 'output', {'name': port, 'num_pins': f'{size}'})
    else:
        sub_tile.append(ET.Comment(' North directional input ports'))
        for port, size in north_input_ports:
            ET.SubElement(sub_tile, 'input', {'name': port, 'num_pins': f'{size}'})
        sub_tile.append(ET.Comment(' North directional output ports'))
        for port, size in north_output_ports:
            ET.SubElement(sub_tile, 'output', {'name': port, 'num_pins': f'{size}'})
        sub_tile.append(ET.Comment(' East directional input ports'))
        for port, size in east_input_ports:
            ET.SubElement(sub_tile, 'input', {'name': port, 'num_pins': f'{size}'})
        sub_tile.append(ET.Comment(' East directional output ports'))
        for port, size in east_output_ports:
            ET.SubElement(sub_tile, 'output', {'name': port, 'num_pins': f'{size}'})
        sub_tile.append(ET.Comment(' South directional input ports'))
        for port, size in south_input_ports:
            ET.SubElement(sub_tile, 'input', {'name': port, 'num_pins': f'{size}'})
        sub_tile.append(ET.Comment(' South directional output ports'))
        for port, size in south_output_ports:
            ET.SubElement(sub_tile, 'output', {'name': port, 'num_pins': f'{size}'})
        sub_tile.append(ET.Comment(' West directional input ports'))
        for port, size in west_input_ports:
            ET.SubElement(sub_tile, 'input', {'name': port, 'num_pins': f'{size}'})
        sub_tile.append(ET.Comment(' West directional output ports'))
        for port, size in west_output_ports:
            ET.SubElement(sub_tile, 'output', {'name': port, 'num_pins': f'{size}'})


    sub_tile.append(ET.Comment(' Set fc_in and fc_out = 0 for all the router-to-router ports and a default value of fc_in=0.10 and fc_out=0.15 for all other core ports'))
    # Create the base fc element with appropriate values for router
    if interface == 'axis' or 'router' in top.lower() or 'noc' in top.lower():
        fc = ET.SubElement(sub_tile, 'fc', {'in_type': 'frac', 'in_val': '0.15', 'out_type': 'frac', 'out_val': '0.10'})

        if directional_in_ports and directional_out_ports:
            # Add comment for directional ports
            fc.append(ET.Comment(' Directional ports '))
            for port, size in directional_in_ports + directional_out_ports:
                ET.SubElement(fc, 'fc_override', {'port_name': port, 'fc_type': 'frac', 'fc_val': '0'})
        else:
            # Add comment for north ports
            fc.append(ET.Comment(' North directional ports '))
            for port, size in north_input_ports + north_output_ports:
                ET.SubElement(fc, 'fc_override', {'port_name': port, 'fc_type': 'frac', 'fc_val': '0'})

            # Add comment for east ports
            fc.append(ET.Comment(' East directional ports '))
            for port, size in east_input_ports + east_output_ports:
                ET.SubElement(fc, 'fc_override', {'port_name': port, 'fc_type': 'frac', 'fc_val': '0'})

            # Add comment for south ports
            fc.append(ET.Comment(' South directional ports '))
            for port, size in south_input_ports + south_output_ports:
                ET.SubElement(fc, 'fc_override', {'port_name': port, 'fc_type': 'frac', 'fc_val': '0'})

            # Add comment for west ports
            fc.append(ET.Comment(' West directional ports '))
            for port, size in west_input_ports + west_output_ports:
                ET.SubElement(fc, 'fc_override', {'port_name': port, 'fc_type': 'frac', 'fc_val': '0'})
    else:
        # For non-router tiles, use the default fc values
        ET.SubElement(sub_tile, 'fc', {'in_type': 'frac', 'in_val': '0.15', 'out_type': 'frac', 'out_val': '0.10'})
    
    # Now create pinlocations with the same grouped ports
    if interface == 'axis' or 'router' in top.lower() or 'noc' in top.lower():
        pinlocations = ET.SubElement(sub_tile, 'pinlocations', {'pattern': 'custom'})
        
        clock_reset_port_names = [f"{top}_tile.{port}" for port in clock_reset_ports]
        core_port_names = [f"{top}_tile.{port}" for port, size in core_input_ports + core_output_ports]
        top_port_names = []
        right_port_names = []
        bottom_port_names = []
        left_port_names = []
        
        # Format the full port names with tile prefix
        if directional_in_ports and directional_out_ports:
                # NORTH = 1;
                # SOUTH = 2;
                # EAST = 3;
                # WEST = 4;
            # divide port into 4 equal indices based on size and append to north, east, south, and west
            #   size will always be divisible by 4 for router ports
                # index_per_side = (size) // 4
                # # new name will be port_name[start_index:end_index] and size will be index_per_side
                # north_input_ports.append((f"{name}[{index_per_side*0}:{index_per_side*1 - 1}]", index_per_side))
                # south_input_ports.append((f"{name}[{index_per_side*1}:{index_per_side*2 - 1}]", index_per_side))  
                # east_input_ports.append((f"{name}[{index_per_side*2}:{index_per_side*3 - 1}]", index_per_side))  
                # west_input_ports.append((f"{name}[{index_per_side*3}:{index_per_side*4 - 1}]", index_per_side))  
            for port, size in directional_in_ports + directional_out_ports:
                index_per_side = (size) // 4
                top_port_names.append(f"{top}_tile.{port}[{index_per_side*0}:{index_per_side*1 - 1}]")
                bottom_port_names.append(f"{top}_tile.{port}[{index_per_side*1}:{index_per_side*2 - 1}]")
                right_port_names.append(f"{top}_tile.{port}[{index_per_side*2}:{index_per_side*3 - 1}]")
                left_port_names.append(f"{top}_tile.{port}[{index_per_side*3}:{index_per_side*4 - 1}]")
        else:
            top_port_names = [f"{top}_tile.{port}" for port, size in north_input_ports + north_output_ports]
            right_port_names = [f"{top}_tile.{port}" for port, size in east_input_ports + east_output_ports]
            bottom_port_names = [f"{top}_tile.{port}" for port, size in south_input_ports + south_output_ports]
            left_port_names = [f"{top}_tile.{port}" for port, size in west_input_ports + west_output_ports]

        # Create location elements for each side
        if top_port_names:
            pinlocations.append(ET.Comment(' Top directional ports '))
            ET.SubElement(pinlocations, 'loc', {'side': 'top', 'xoffset': '0', 'yoffset': f'{tile_size_y}'}).text = " ".join(top_port_names)
        if right_port_names:
            pinlocations.append(ET.Comment(' Right directional ports '))
            ET.SubElement(pinlocations, 'loc', {'side': 'right', 'xoffset': f'{tile_size_x}', 'yoffset': '0'}).text = " ".join(right_port_names)
        if bottom_port_names:
            pinlocations.append(ET.Comment(' Bottom directional ports '))
            ET.SubElement(pinlocations, 'loc', {'side': 'bottom', 'xoffset': '0', 'yoffset': '0'}).text = " ".join(bottom_port_names)
        if left_port_names:
            pinlocations.append(ET.Comment(' Left directional ports '))
            ET.SubElement(pinlocations, 'loc', {'side': 'left', 'xoffset': '0', 'yoffset': '0'}).text = " ".join(left_port_names)
        
        for port, size in core_input_ports:
            if "data" in port.lower():
                data_in_port_name = f"{top}_tile.{port}"
                data_in_port_size = size
        for port, size in core_output_ports:
            if "data" in port.lower():
                data_out_port_name = f"{top}_tile.{port}"
                data_out_port_size = size
        
        #  Partition 10 inputs and 10 output pins per offset
        #  data in port size and out port size will be same
        pinlocations.append(ET.Comment(' Data input and output ports partitioned every 10 pins on left and right sides '))
        if data_in_port_name and data_out_port_name:
            num_partitions = (data_in_port_size + 9) // 10  # Ceiling division
            # half of these partitions on left and half on right
            for i in range(num_partitions):
                xoffset = 0 if i < (num_partitions + 1) // 2 else tile_size_x
                yoffset = (i % ((num_partitions + 1) // 2)) + 1  # Spread along y-axis
                start_idx = i * 10
                end_idx = min(start_idx + 10, data_in_port_size)
                in_ports_partition = [f"{data_in_port_name}[{j}]" for j in range(start_idx, end_idx)]
                out_ports_partition = [f"{data_out_port_name}[{j}]" for j in range(start_idx, end_idx)]
                ET.SubElement(pinlocations, 'loc', {'side': 'left' if xoffset == 0 else 'right', 'xoffset': str(xoffset), 'yoffset': str(yoffset)}).text = " ".join(in_ports_partition+out_ports_partition)
                # ET.SubElement(pinlocations, 'loc', {'side': 'left' if xoffset == 0 else 'right', 'xoffset': str(xoffset), 'yoffset': str(yoffset + 1)}).text = " ".join(out_ports_partition)

        #  all remaining core ports and clk reset on top and bottom
        remaining_core_ports = [port for port in core_port_names + clock_reset_port_names if port not in (data_in_port_name, data_out_port_name)]
        if remaining_core_ports:
            pinlocations.append(ET.Comment(' Remaining core ports and clock/reset ports '))
            # Split half on top and half on bottom
            half_index = (len(remaining_core_ports) + 1) // 2
            top_ports = remaining_core_ports[:half_index]
            bottom_ports = remaining_core_ports[half_index:]
            if top_ports:
                ET.SubElement(pinlocations, 'loc', {'side': 'top', 'xoffset': '1', 'yoffset': f'{tile_size_y}'}).text = " ".join(top_ports)
            if bottom_ports:
                ET.SubElement(pinlocations, 'loc', {'side': 'bottom', 'xoffset': '1', 'yoffset': '0'}).text = " ".join(bottom_ports)

    else:
        # For non-router tiles, use the default spread pattern
        ET.SubElement(sub_tile, 'pinlocations', {'pattern': 'spread'})

    indent_xml(new_tile, level=2)
    models_element = root.find('.//tiles')
    models_element.append(new_tile)
    tree.write(vpr_arch_file)
    # print(f" ---------- Added tile '{top}_tile' in VPR arch file at {vpr_arch_file}")

# def add_vpr_pb_type(top, port_dict, has_clock, clock_port, vpr_arch_file, root, tree):
def add_vpr_pb_type(top, 
                    # port_dict, 
                    directional_in_ports, directional_out_ports,
                    north_input_ports, north_output_ports, east_input_ports, east_output_ports, south_input_ports, south_output_ports, west_input_ports, west_output_ports, core_input_ports, core_output_ports, clock_reset_ports,
                    has_clock, clock_port, vpr_arch_file, vpr_root, vpr_tree):
    # Create the new <pb_type> tag
    new_pb_type = ET.Element('pb_type', {'name': f'{top}_tile'})
    new_pb_type.append(ET.Comment('Clock and reset ports'))
    for port in clock_reset_ports:
        if port == clock_port:
            ET.SubElement(new_pb_type, 'clock', {'name': port, 'num_pins': '1'})
        else:
            ET.SubElement(new_pb_type, 'input', {'name': port, 'num_pins': '1'})
    new_pb_type.append(ET.Comment('Core input ports'))
    for port, size in core_input_ports:
        ET.SubElement(new_pb_type, 'input', {'name': port, 'num_pins': str(size)})
    new_pb_type.append(ET.Comment('Core output ports'))
    for port, size in core_output_ports:
        ET.SubElement(new_pb_type, 'output', {'name': port, 'num_pins': str(size)})

    new_pb_type.append(ET.Comment('Router-to-router ports'))
    if directional_in_ports and directional_out_ports:
        new_pb_type.append(ET.Comment(' Input directional ports'))
        for port, size in directional_in_ports:
            ET.SubElement(new_pb_type, 'input', {'name': port, 'num_pins': str(size)})
        new_pb_type.append(ET.Comment(' Output directional ports'))
        for port, size in directional_out_ports:
            ET.SubElement(new_pb_type, 'output', {'name': port, 'num_pins': str(size)})
    else:
        new_pb_type.append(ET.Comment('North directional input ports'))
        for port, size in north_input_ports:
            ET.SubElement(new_pb_type, 'input', {'name': port, 'num_pins': str(size)})
        new_pb_type.append(ET.Comment('North directional output ports'))
        for port, size in north_output_ports:
            ET.SubElement(new_pb_type, 'output', {'name': port, 'num_pins': str(size)})

        new_pb_type.append(ET.Comment('East directional input ports'))
        for port, size in east_input_ports:
            ET.SubElement(new_pb_type, 'input', {'name': port, 'num_pins': str(size)})
        new_pb_type.append(ET.Comment('East directional output ports'))
        for port, size in east_output_ports:
            ET.SubElement(new_pb_type, 'output', {'name': port, 'num_pins': str(size)})

        new_pb_type.append(ET.Comment('South directional input ports'))
        for port, size in south_input_ports:
            ET.SubElement(new_pb_type, 'input', {'name': port, 'num_pins': str(size)})
        new_pb_type.append(ET.Comment('South directional output ports'))
        for port, size in south_output_ports:
            ET.SubElement(new_pb_type, 'output', {'name': port, 'num_pins': str(size)})

        new_pb_type.append(ET.Comment('West directional input ports'))
        for port, size in west_input_ports:
            ET.SubElement(new_pb_type, 'input', {'name': port, 'num_pins': str(size)})
        new_pb_type.append(ET.Comment('West directional output ports'))
        for port, size in west_output_ports:
            ET.SubElement(new_pb_type, 'output', {'name': port, 'num_pins': str(size)})

# physical mode - not used in PnR
    mode_0 = ET.SubElement(new_pb_type, 'mode', {'name': 'physical'})
    mode_0.append(ET.Comment('This mode will have both core ports and router-to-router ports'))
    mode_0.append(ET.Comment('Is not used in PnR, but required for OpenFPGA flow'))
    pb_type_0 = ET.SubElement(mode_0, 'pb_type', {'name': f'{top}_physical', 'blif_model': f'.subckt {top}_physical', 'num_pb': '1'})
    pb_type_0.append(ET.Comment('Clock and reset ports'))
    for port in clock_reset_ports:
        if port == clock_port:
            ET.SubElement(pb_type_0, 'clock', {'name': clock_port, 'num_pins': '1'})
        else:
            ET.SubElement(pb_type_0, 'input', {'name': port, 'num_pins': '1'})
    pb_type_0.append(ET.Comment('Core input ports'))
    for port, size in core_input_ports:
        ET.SubElement(pb_type_0, 'input', {'name': port, 'num_pins': str(size)})
    pb_type_0.append(ET.Comment('Core output ports'))
    for port, size in core_output_ports:
        ET.SubElement(pb_type_0, 'output', {'name': port, 'num_pins': str(size)})
    pb_type_0.append(ET.Comment('Router-to-router ports'))
    if directional_in_ports and directional_out_ports:
        pb_type_0.append(ET.Comment(' Input directional ports'))
        for port, size in directional_in_ports:
            ET.SubElement(pb_type_0, 'input', {'name': port, 'num_pins': str(size)})
        pb_type_0.append(ET.Comment(' Output directional ports'))
        for port, size in directional_out_ports:
            ET.SubElement(pb_type_0, 'output', {'name': port, 'num_pins': str(size)})
    else:
        pb_type_0.append(ET.Comment('North directional input ports'))
        for port, size in north_input_ports:
            ET.SubElement(pb_type_0, 'input', {'name': port, 'num_pins': str(size)})
        pb_type_0.append(ET.Comment('North directional output ports'))
        for port, size in north_output_ports:
            ET.SubElement(pb_type_0, 'output', {'name': port, 'num_pins': str(size)})
        pb_type_0.append(ET.Comment('East directional input ports'))
        for port, size in east_input_ports:
            ET.SubElement(pb_type_0, 'input', {'name': port, 'num_pins': str(size)})
        pb_type_0.append(ET.Comment('East directional output ports'))
        for port, size in east_output_ports:
            ET.SubElement(pb_type_0, 'output', {'name': port, 'num_pins': str(size)})
        pb_type_0.append(ET.Comment('South directional input ports'))
        for port, size in south_input_ports:
            ET.SubElement(pb_type_0, 'input', {'name': port, 'num_pins': str(size)})
        pb_type_0.append(ET.Comment('South directional output ports'))
        for port, size in south_output_ports:
            ET.SubElement(pb_type_0, 'output', {'name': port, 'num_pins': str(size)})
        pb_type_0.append(ET.Comment('West directional input ports'))
        for port, size in west_input_ports:
            ET.SubElement(pb_type_0, 'input', {'name': port, 'num_pins': str(size)})
        pb_type_0.append(ET.Comment('West directional output ports'))
        for port, size in west_output_ports:
            ET.SubElement(pb_type_0, 'output', {'name': port, 'num_pins': str(size)})

    # timing constraints for physical mode
    pb_type_0.append(ET.Comment('Timing constraints'))
    if has_clock:
        pb_type_0.append(ET.Comment('Input timing constraints'))
        for port, size in core_input_ports:
            ET.SubElement(pb_type_0, 'T_setup', {'value': '66e-12', 'port': f'{top}_physical.{port}', 'clock': clock_port})
            ET.SubElement(pb_type_0, 'T_clock_to_Q', {'max': '42e-12', 'min': '37e-12', 'port': f'{top}_physical.{port}', 'clock': clock_port})
        # input constraints for reset
        for port in clock_reset_ports:
            if port != clock_port:
                ET.SubElement(pb_type_0, 'T_setup', {'value': '66e-12', 'port': f'{top}_physical.{port}', 'clock': clock_port})
                ET.SubElement(pb_type_0, 'T_clock_to_Q', {'max': '42e-12', 'min': '37e-12', 'port': f'{top}_physical.{port}', 'clock': clock_port})
        # directional input ports
        for port, size in north_input_ports + east_input_ports + south_input_ports + west_input_ports + directional_in_ports:
            ET.SubElement(pb_type_0, 'T_setup', {'value': '66e-12', 'port': f'{top}_physical.{port}', 'clock': clock_port})
            ET.SubElement(pb_type_0, 'T_clock_to_Q', {'max': '42e-12', 'min': '37e-12', 'port': f'{top}_physical.{port}', 'clock': clock_port})
        pb_type_0.append(ET.Comment('Output timing constraints'))
        for port, size in core_output_ports:
            ET.SubElement(pb_type_0, 'T_setup', {'value': '66e-12', 'port': f'{top}_physical.{port}', 'clock': clock_port})
            ET.SubElement(pb_type_0, 'T_clock_to_Q', {'max': '42e-12', 'min': '37e-12', 'port': f'{top}_physical.{port}', 'clock': clock_port})
        # directional output ports
        pb_type_0.append(ET.Comment('Directional output ports timing constraints'))
        for port, size in north_output_ports + east_output_ports + south_output_ports + west_output_ports + directional_out_ports:
            ET.SubElement(pb_type_0, 'T_setup', {'value': '66e-12', 'port': f'{top}_physical.{port}', 'clock': clock_port})
            ET.SubElement(pb_type_0, 'T_clock_to_Q', {'max': '42e-12', 'min': '37e-12', 'port': f'{top}_physical.{port}', 'clock': clock_port})

        # delay constant
        for port_out, size_out in core_output_ports + north_output_ports + east_output_ports + south_output_ports + west_output_ports + directional_out_ports:
            for port_in, size_in in core_input_ports:
                ET.SubElement(pb_type_0, 'delay_constant', {'max': '1.78e-9', 'in_port': f'{top}_physical.{port_in}', 'out_port': f'{top}_physical.{port_out}'})
            for port_in in clock_reset_ports:
                if port_in != clock_port:
                    ET.SubElement(pb_type_0, 'delay_constant', {'max': '1.78e-9', 'in_port': f'{top}_physical.{port_in}', 'out_port': f'{top}_physical.{port_out}'})
            for port_in, size_in in north_input_ports + east_input_ports + south_input_ports + west_input_ports + directional_in_ports:
                ET.SubElement(pb_type_0, 'delay_constant', {'max': '1.78e-9', 'in_port': f'{top}_physical.{port_in}', 'out_port': f'{top}_physical.{port_out}'})

    pb_type_0.append(ET.Comment('Interconnects to top-level pb_type: Did not include a local crossbar'))
    interconnect_0 = ET.SubElement(mode_0, 'interconnect')

    for port in clock_reset_ports:
        ET.SubElement(interconnect_0, 'direct', {'name': f'phy_connection_{port}', 'input': f'{top}_tile.{port}', 'output': f'{top}_physical.{port}'})
    
    for port, size in core_input_ports:
        ET.SubElement(interconnect_0, 'direct', {'name': f'phy_connection_{port}', 'input': f'{top}_tile.{port}', 'output': f'{top}_physical.{port}'})
    for port, size in north_input_ports + east_input_ports + south_input_ports + west_input_ports + directional_in_ports:
        ET.SubElement(interconnect_0, 'direct', {'name': f'phy_connection_{port}', 'input': f'{top}_tile.{port}', 'output': f'{top}_physical.{port}'})

    for port, size in core_output_ports:
        ET.SubElement(interconnect_0, 'direct', {'name': f'phy_connection_{port}', 'input': f'{top}_physical.{port}', 'output': f'{top}_tile.{port}'})
    for port, size in north_output_ports + east_output_ports + south_output_ports + west_output_ports + directional_out_ports:
        ET.SubElement(interconnect_0, 'direct', {'name': f'phy_connection_{port}', 'input': f'{top}_physical.{port}', 'output': f'{top}_tile.{port}'})


# logical mode used in PnR
    new_pb_type.append(ET.Comment('Logical mode used in PnR'))
    mode_1 = ET.SubElement(new_pb_type, 'mode', {'name': top})
    mode_1.append(ET.Comment('This mode will only have core ports, no router-to-router ports'))
    pb_type_1 = ET.SubElement(mode_1, 'pb_type', {'name': top, 'blif_model': f'.subckt {top}', 'num_pb': '1'})

    pb_type_1.append(ET.Comment('Clock and reset ports'))
    for port in clock_reset_ports:
        if port == clock_port:
            ET.SubElement(pb_type_1, 'clock', {'name': clock_port, 'num_pins': '1'})
        else:
            ET.SubElement(pb_type_1, 'input', {'name': port, 'num_pins': '1'})
    pb_type_1.append(ET.Comment('Core input ports'))
    for port, size in core_input_ports:
        ET.SubElement(pb_type_1, 'input', {'name': port, 'num_pins': str(size)})
    pb_type_1.append(ET.Comment('Core output ports'))
    for port, size in core_output_ports:
        ET.SubElement(pb_type_1, 'output', {'name': port, 'num_pins': str(size)})


    pb_type_1.append(ET.Comment('Timing constraints'))
    if has_clock:
        pb_type_1.append(ET.Comment('Input timing constraints'))
        for port, size in core_input_ports:
            ET.SubElement(pb_type_1, 'T_setup', {'value': '66e-12', 'port': f'{top}.{port}', 'clock': clock_port})
            ET.SubElement(pb_type_1, 'T_clock_to_Q', {'max': '42e-12', 'min': '37e-12', 'port': f'{top}.{port}', 'clock': clock_port})
        # input constraints for reset
        for port in clock_reset_ports:
            if port != clock_port:
                ET.SubElement(pb_type_1, 'T_setup', {'value': '66e-12', 'port': f'{top}.{port}', 'clock': clock_port})
                ET.SubElement(pb_type_1, 'T_clock_to_Q', {'max': '42e-12', 'min': '37e-12', 'port': f'{top}.{port}', 'clock': clock_port})

        pb_type_1.append(ET.Comment('Output timing constraints'))
        for port, size in core_output_ports:
            ET.SubElement(pb_type_1, 'T_setup', {'value': '66e-12', 'port': f'{top}.{port}', 'clock': clock_port})
            ET.SubElement(pb_type_1, 'T_clock_to_Q', {'max': '42e-12', 'min': '37e-12', 'port': f'{top}.{port}', 'clock': clock_port})

        # delay constant
        for port_out, size_out in core_output_ports:
            for port_in, size_in in core_input_ports:
                ET.SubElement(pb_type_1, 'delay_constant', {'max': '1.78e-9', 'in_port': f'{top}.{port_in}', 'out_port': f'{top}.{port_out}'})
            for port_in in clock_reset_ports:
                if port_in != clock_port:
                    ET.SubElement(pb_type_1, 'delay_constant', {'max': '1.78e-9', 'in_port': f'{top}.{port_in}', 'out_port': f'{top}.{port_out}'})
        

    pb_type_1.append(ET.Comment('Interconnects to top-level pb_type: Did not include a local crossbar'))
    interconnect_1 = ET.SubElement(mode_1, 'interconnect')

    for port in clock_reset_ports:
        ET.SubElement(interconnect_1, 'direct', {'name': f'connection_{port}', 'input': f'{top}_tile.{port}', 'output': f'{top}.{port}'})

    for port, size in core_input_ports:
        ET.SubElement(interconnect_1, 'direct', {'name': f'connection_{port}', 'input': f'{top}_tile.{port}', 'output': f'{top}.{port}'})

    for port, size in core_output_ports:
        ET.SubElement(interconnect_1, 'direct', {'name': f'connection_{port}', 'input': f'{top}.{port}', 'output': f'{top}_tile.{port}'})

    indent_xml(new_pb_type, level=1)

    models_element = vpr_root.find('.//complexblocklist')
    models_element.append(new_pb_type)

    vpr_tree.write(vpr_arch_file)
    # print(f" ---------- Added pb_type '{top}_tile' in VPR arch file")

def add_openfpga_circuit_model(top, verilog_file, spice_file, port_dict, has_clock, clock_port, openfpga_arch_file, root, tree):
    # Create the new <model> tag
    new_circuit_model = ET.Element('circuit_model', {'type': 'hard_logic', 'name': top, 'prefix': top, 'is_default': 'false', 'spice_netlist': spice_file, 'verilog_netlist': verilog_file})
    design_technology = ET.SubElement(new_circuit_model, 'design_technology', {'type': 'cmos'})
    input_buffer = ET.SubElement(new_circuit_model, 'input_buffer', {'exist': 'true', 'circuit_model_name': 'INVTX1'})
    output_buffer = ET.SubElement(new_circuit_model, 'output_buffer', {'exist': 'true', 'circuit_model_name': 'INVTX1'})
   
    for input_port in port_dict[top]["inputs"]:
        for name, size in input_port.items():
            if name == clock_port:
                ET.SubElement(new_circuit_model, 'port', {'type': 'clock', 'prefix': name, 'size': '1', 'is_global': 'true', 'is_clock': 'true'})
            else:
                ET.SubElement(new_circuit_model, 'port', {'type': 'input', 'prefix': name, 'lib_name': name, 'size': f'{size}'})
    for output_port in port_dict[top]["outputs"]:
        for name, size in output_port.items():
            ET.SubElement(new_circuit_model, 'port', {'type': 'output', 'prefix': name, 'lib_name': name, 'size': f'{size}'})

    # Indent 
    indent_xml(new_circuit_model, level=2)

    # Find the <models> tag
    circuit_library_element = root.find('.//circuit_library')

    circuit_library_element.append(new_circuit_model)
    tree.write(openfpga_arch_file)
    # print(f" ---------- Added circuit model '{top}' in openfpga arch file")

def add_openfpga_pb_type_annotation(top, openfpga_arch_file, root, tree):
    # Create the new <model> tag
    pb_type_top = ET.Element('pb_type', {'name': f'{top}_tile', 'physical_mode_name': "physical"})
    pb_type_physical = ET.Element('pb_type', {'name': f'{top}_tile[physical].{top}_physical', 'circuit_model_name': top})
    pb_type_primitive = ET.Element('pb_type', {'name': f'{top}_tile[{top}].{top}', 'physical_pb_type_name': f'{top}_tile[physical].{top}_physical'})

#   <pb_type name="router_wrap_tile" physical_mode_name="physical"/>
#    <pb_type name="router_wrap_tile[physical].router_wrap_physical" circuit_model_name="router_wrap"/>
#    <pb_type name="router_wrap_tile[router_wrap].router_wrap" physical_pb_type_name="router_wrap_tile[physical].router_wrap_physical"/>
    # Indent
    indent_xml(pb_type_top, level=1)
    indent_xml(pb_type_physical, level=1)
    indent_xml(pb_type_primitive, level=1)

    pb_type_annotations_element = root.find('.//pb_type_annotations')

    pb_type_annotations_element.append(pb_type_top)
    pb_type_annotations_element.append(pb_type_physical)
    pb_type_annotations_element.append(pb_type_primitive)

    tree.write(openfpga_arch_file)
    # print(f" ---------- Added pb_type annotation '{top}' in openfpga arch file")

# def add_vpr_direct_connections(top, port_dict, has_clock, clock_port, arch_dir, root, tree):
#     # Create the new <model> tag
#     new_model = ET.Element('model', {'name': top})
#     input_ports = ET.SubElement(new_model, 'input_ports')
#     output_ports = ET.SubElement(new_model, 'output_ports')

# def add_layout_tag(top, port_dict, has_clock, clock_port, vpr_arch_file, vpr_root, vpr_tree):
def add_vpr_layout_tag(top, port_dict, has_clock, clock_port, vpr_arch_file, vpr_root, vpr_tree):
    # Find the <layout> tag or create it if it doesn't exist
    layout_element = vpr_root.find('.//layout')

    # Create the fixed_layout element
    fixed_layout = ET.SubElement(layout_element, 'fixed_layout', {'name': 'pbf_noc', 'width': '70', 'height': '70'})
    
    # Add comment for layer 0
    fixed_layout.append(ET.Comment(' <layer die="0"> '))
    
    # Add perimeter and corners
    ET.SubElement(fixed_layout, 'perimeter', {'type': 'io', 'priority': '100'})
    ET.SubElement(fixed_layout, 'corners', {'type': 'EMPTY', 'priority': '101'})
    
    # Add fill with 'clb'
    ET.SubElement(fixed_layout, 'fill', {'type': 'clb', 'priority': '10'})
    
    # Add column of memory
    ET.SubElement(fixed_layout, 'col', {
        'type': 'memory',
        'startx': '2',
        'starty': '1',
        'repeatx': '8',
        'priority': '20'
    })
    ET.SubElement(fixed_layout, 'col', {
        'type': 'EMPTY',
        'startx': '2',
        'starty': '1',
        'repeatx': '8',
        'priority': '19'
    })

    # Add column of mult
    ET.SubElement(fixed_layout, 'col', {
        'type': 'mult_36',
        'startx': '6',
        'starty': '1',
        'repeatx': '8',
        'priority': '20'
    })
    ET.SubElement(fixed_layout, 'col', {
        'type': 'EMPTY',
        'startx': '6',
        'starty': '1',
        'repeatx': '8',
        'priority': '19'
    })
    
    # Add comment for end of layer 0
    fixed_layout.append(ET.Comment(' </layer> '))
    
    # Add comment for layer -1
    fixed_layout.append(ET.Comment(' <layer die="-1"> '))
    
    # Add grid of router tiles
    x_positions = [10, 25, 40, 55]
    y_positions = [10, 25, 40, 55]
    
    for x in x_positions:
        for y in y_positions:
            ET.SubElement(fixed_layout, 'single', {
                'type': f'{top}_tile',
                'x': str(x),
                'y': str(y),
                'priority': '50'
            })
    
    # Add comment for end of layer -1
    fixed_layout.append(ET.Comment(' </layer> '))
    
    # Indent the XML for readability
    indent_xml(fixed_layout, level=1)
    
    # Write the updated tree to the file
    vpr_tree.write(vpr_arch_file)
    # print(f" ---------- Added fixed layout for '{top}_tile' in VPR arch file")

def add_vpr_noc_tag(top, vpr_arch_file, vpr_root, vpr_tree):
    # Find the architecture root to append the noc element
    architecture = vpr_root
    
    # Create the noc element with attributes
    noc_element = ET.Element('noc', {
        'link_bandwidth': '1e6',
        'router_latency': '1e-9',
        'link_latency': '1e-9',
        'noc_router_tile_name': f'{top}_tile'
    })

    # if 'mesh' in noc_params:    
    #     if noc_params['mesh']['X'] == noc_params['mesh']['Y']:
    #     # Create the mesh element
    #         mesh = ET.SubElement(noc_element, 'mesh', { 'startx': '2', 'starty': '2', 'endx': '70', 'endy': '70', 'size': noc_params['mesh']['X']})
    #     else:
    #         for i in range(noc_params['mesh']['X']):
    #             for j in range(noc_params['mesh']['Y']):
    #                 ET.SubElement(mesh, 'single', { 'x': str(2 + 15 * i), 'y': str(2 + 15 * j)})


    # Create the topology element
    topology = ET.SubElement(noc_element, 'topology')
    
    # Define the router positions (same as in the fixed layout)
    x_positions = [10, 25, 40, 55]
    y_positions = [10, 25, 40, 55]
    
    # Define connections for each router in a 4x4 mesh
    # Initialize router IDs
    router_ids = {}
    for y_idx, y in enumerate(y_positions):
        for x_idx, x in enumerate(x_positions):
            router_id = y_idx * 4 + x_idx
            router_ids[(x, y)] = router_id
    
    # Create router elements with connections
    for y_idx, y in enumerate(y_positions):
        for x_idx, x in enumerate(x_positions):
            router_id = router_ids[(x, y)]
            
            # Determine connections to neighboring routers
            connections = []
            
            # Check west neighbor
            if x_idx > 0:
                connections.append(router_ids[(x_positions[x_idx-1], y)])
                
            # Check east neighbor
            if x_idx < 3:
                connections.append(router_ids[(x_positions[x_idx+1], y)])
                
            # Check north neighbor
            if y_idx > 0:
                connections.append(router_ids[(x, y_positions[y_idx-1])])
                
            # Check south neighbor
            if y_idx < 3:
                connections.append(router_ids[(x, y_positions[y_idx+1])])
            
            # Create router element
            router_element = ET.SubElement(topology, 'router', {
                'id': str(router_id),
                'positionx': str(x),
                'positiony': str(y),
                'connections': ' '.join(map(str, connections))
            })
    
    # Indent the XML for readability
    indent_xml(noc_element)
    
    # Add the noc element to the architecture
    architecture.append(noc_element)
    
    # Write the updated tree to the file
    vpr_tree.write(vpr_arch_file)
    # print(f" ---------- Added NoC mesh topology for '{top}_tile' in VPR arch file")

def add_openfpga_noc_tag(top, 
                        #  port_dict,
                         directional_in_ports, directional_out_ports,
                        north_input_ports, north_output_ports, east_input_ports, east_output_ports, south_input_ports, south_output_ports, west_input_ports, west_output_ports,
                        core_input_ports, core_output_ports, clock_reset_ports,
                        openfpga_arch_file, openfpga_root, openfpga_tree):
    # print(f"Adding NoC annotation tag to OpenFPGA arch file for {top}")
    
    # Create port classification for directional routing
    top_in_ports = []
    top_out_ports = []
    right_in_ports = []
    right_out_ports = []
    bottom_in_ports = []
    bottom_out_ports = []
    left_in_ports = []
    left_out_ports = []
    
    # Classify input ports by direction
    if directional_in_ports and directional_out_ports:
        # NORTH = 1;
        # SOUTH = 2;
        # EAST = 3;
        # WEST = 4;
        # divide port into 4 equal indices based on size and append to north, east, south, and west
        #   size will always be divisible by 4 for router ports
            # index_per_side = (size) // 4
            # # new name will be port_name[start_index:end_index] and size will be index_per_side
        for port, size in directional_in_ports:
            index_per_side = (size) // 4
            if index_per_side > 1:
                top_in_ports.append(f"{port}[{index_per_side*0}:{index_per_side*1 - 1}]")
                bottom_in_ports.append(f"{port}[{index_per_side*1}:{index_per_side*2 - 1}]")
                right_in_ports.append(f"{port}[{index_per_side*2}:{index_per_side*3 - 1}]")
                left_in_ports.append(f"{port}[{index_per_side*3}:{index_per_side*4 - 1}]")
            if index_per_side == 1:
                top_in_ports.append(f"{port}[0]")
                bottom_in_ports.append(f"{port}[1]")
                right_in_ports.append(f"{port}[2]")
                left_in_ports.append(f"{port}[3]")
        # Classify output ports by direction
        for port, size in directional_out_ports:
            index_per_side = (size) // 4
            if index_per_side > 1:
                top_out_ports.append(f"{port}[{index_per_side*0}:{index_per_side*1 - 1}]")
                bottom_out_ports.append(f"{port}[{index_per_side*1}:{index_per_side*2 - 1}]")
                right_out_ports.append(f"{port}[{index_per_side*2}:{index_per_side*3 - 1}]")
                left_out_ports.append(f"{port}[{index_per_side*3}:{index_per_side*4 - 1}]")
            if index_per_side == 1:
                top_out_ports.append(f"{port}[0]")
                bottom_out_ports.append(f"{port}[1]")
                right_out_ports.append(f"{port}[2]")
                left_out_ports.append(f"{port}[3]")
    else:
        top_in_ports = [f"{port}" for port, size in north_input_ports]
        top_out_ports = [f"{port}" for port, size in north_output_ports]
        right_in_ports = [f"{port}" for port, size in east_input_ports]
        right_out_ports = [f"{port}" for port, size in east_output_ports]
        bottom_in_ports = [f"{port}" for port, size in south_input_ports]
        bottom_out_ports = [f"{port}" for port, size in south_output_ports]
        left_in_ports = [f"{port}" for port, size in west_input_ports]
        left_out_ports = [f"{port}" for port, size in west_output_ports]



    noc_annotation = ET.Element('noc_annotation', {'noc_router_tile_name': top})
    
    noc_links = ET.SubElement(noc_annotation, 'noc_links', {
        'link_type': 'hard', 
        'circuit_model': 'direct_interc'
    })
    
    ET.SubElement(noc_links, 'noc_port', {
        'side': 'top',
        'input_pins': ' '.join(top_in_ports),
        'output_pins': ' '.join(top_out_ports)
    })
    
    ET.SubElement(noc_links, 'noc_port', {
        'side': 'right',
        'input_pins': ' '.join(right_in_ports),
        'output_pins': ' '.join(right_out_ports)
    })
    
    ET.SubElement(noc_links, 'noc_port', {
        'side': 'bottom',
        'input_pins': ' '.join(bottom_in_ports),
        'output_pins': ' '.join(bottom_out_ports)
    })
    
    ET.SubElement(noc_links, 'noc_port', {
        'side': 'left',
        'input_pins': ' '.join(left_in_ports),
        'output_pins': ' '.join(left_out_ports)
    })
    
    indent_xml(noc_annotation)
    openfpga_root.append(noc_annotation)
    
    openfpga_tree.write(openfpga_arch_file)
    # print(f" ---------- Added NoC annotation for '{top}' in OpenFPGA arch file")

def generate_arch_files(yosys_path, verilog_file, spice_file, top, output_dir, vpr_arch, openfpga_arch, is_noc):
    interface = 'axis' 
# def generate_arch_files(name, yosys_path, verilog_file, spice_file, top, vpr_output_dir, openpfga_output_dir, temp_dir, vpr_arch, openfpga_arch):
    # Set defaults paths
    if not yosys_path:
        if not os.getenv('OPENFPGA_PATH'):
            print("---- ERROR: Please set OPENFPGA_PATH environment variable or provide -yosys_path")
            exit(1)
        yosys_path = os.getenv('OPENFPGA_PATH', '') + '/build/yosys/bin/yosys'
    if not vpr_arch:
        # vpr_arch = os.getenv('OPENFPGA_PATH', '') + '/openfpga_flow/vpr_arch/k6_frac_N10_40nm.xml'
        vpr_arch = os.getenv('OPENFPGA_PATH', '') + '/openfpga_flow/vpr_arch/k6_frac_N10_tileable_adder_chain_dpram8K_dsp36_fracff_40nm.xml'
        print(f"---- WARNING: Template VPR arch file not found using default file at: {vpr_arch}")
    if not openfpga_arch:
        # openfpga_arch = os.getenv('OPENFPGA_PATH', '') + '/openfpga_flow/openfpga_arch/k6_frac_N10_40nm_openfpga.xml'
        openfpga_arch = os.getenv('OPENFPGA_PATH', '') + '/openfpga_flow/openfpga_arch/k6_frac_N10_adder_chain_dpram8K_dsp36_fracff_40nm_openfpga.xml'
        print(f"---- WARNING: Template OpenFPGA arch file not found using default file at: {openfpga_arch}")
    if not spice_file:
        print("---- WARNING: Spice file not provided, using verilog file as spice file")
        spice_file = verilog_file

    vpr_output_dir = output_dir
    openfpga_output_dir = output_dir
    temp_dir = output_dir
    task_dir = temp_dir
    # copy vpr template to current arch dir
    # shutil.copy(f'{vpr_arch}', f'{vpr_output_dir}/{name}_vpr.xml')
    # vpr_arch_file = f'{vpr_output_dir}/{name}_vpr.xml'
    # print(60*'*')
    # print(f"vpr arch template: {vpr_arch}")
    # print(f"output dir: {vpr_output_dir}")
    shutil.copy(f'{vpr_arch}', f'{vpr_output_dir}/vpr_arch.xml')
    vpr_arch_file = f'{vpr_output_dir}/vpr_arch.xml'

    # copy vpr template to current arch dir
    # shutil.copy(f'{openfpga_arch}', f'{openpfga_output_dir}/{name}_openfpga.xml')
    # openfpga_arch_file = f'{openpfga_output_dir}/{name}_openfpga.xml'
    shutil.copy(f'{openfpga_arch}', f'{openfpga_output_dir}/openfpga_arch.xml')
    openfpga_arch_file = f'{openfpga_output_dir}/openfpga_arch.xml'

    # generate portlist.txt with yosys
    yosys_command = f"{yosys_path} -p 'read_verilog -nowb -sv -noopt  {verilog_file}; tee -o {task_dir}/portlist.txt portlist {top}'"

    try:
        result = subprocess.run(yosys_command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        # print(f"Generated hardblock portlist fromm verilog file at $task_dir/portlist.txt")
    except subprocess.CalledProcessError as e:
        print(f"ERROR: An error occurred: {e.stderr}")

    port_dict = {}

    with open(f'{task_dir}/portlist.txt', 'r') as file:
        lines = file.readlines()
        module_name = ""
        inputs = []
        outputs = []
        
        for line in lines:
            line = line.strip()
            if line.startswith("module"):
                module_name = line.split()[1]
                port_dict[module_name] = {"inputs": [], "outputs": []}
            elif line.startswith("input"):
                size_str = line.split()[1]
                name = line.split()[2]
                size = parse_size(size_str)
                port_dict[module_name]["inputs"].append({name: size})
            elif line.startswith("output"):
                size_str = line.split()[1]
                name = line.split()[2]
                size = parse_size(size_str)
                port_dict[module_name]["outputs"].append({name: size})

    if not port_dict:
        print("ERROR: Could not generate portlist from verilog file")
        exit(1)

    # Check if there is a clock in inputs of port_dict
    has_clock = False
    for input_port in port_dict[top]["inputs"]:
        for name, size in input_port.items():
            if name.startswith("clk") or name.lower() == "clock":
                has_clock = True
                clock_port = name
                break
        if has_clock:
            break
        
    if not has_clock:
        print(" --- Does not have a clock signal")


    # First collect all ports by direction 
    north_input_ports = []
    north_output_ports = []
    east_input_ports = []
    east_output_ports = []
    south_input_ports = []
    south_output_ports = []
    west_input_ports = []
    west_output_ports = []
    core_input_ports = []
    core_output_ports = []
    clock_reset_ports = []
    directional_in_ports = []
    directional_out_ports = []
    # directional_ports = {directional_in_ports, directional_out_ports} 

    # Group ports by direction (based on naming conventions)
    for input_port in port_dict[top]["inputs"]:
        for name, size in input_port.items():
            if name == clock_port or 'clk' in name.lower() or 'rst' in name.lower() or 'reset' in name.lower():
                clock_reset_ports.append(name)
            elif (interface == 'axis' and 'axis' in name.lower()) or 'address' in name.lower():
                core_input_ports.append((name, size))
            elif 'top' in name.lower() or 'north' in name.lower():
                north_input_ports.append((name, size))
            elif 'right' in name.lower() or 'east' in name.lower():
                east_input_ports.append((name, size))
            elif 'bottom' in name.lower() or 'south' in name.lower():
                south_input_ports.append((name, size))
            elif 'left' in name.lower() or 'west' in name.lower():
                west_input_ports.append((name, size))
            else:
                directional_in_ports.append((name, size))
                # NORTH = 1;
                # SOUTH = 2;
                # EAST = 3;
                # WEST = 4;
            # divide port into 4 equal indices based on size and append to north, east, south, and west
            #   size will always be divisible by 4 for router ports
                # index_per_side = (size) // 4
                # # new name will be port_name[start_index:end_index] and size will be index_per_side
                # north_input_ports.append((f"{name}[{index_per_side*0}:{index_per_side*1 - 1}]", index_per_side))
                # south_input_ports.append((f"{name}[{index_per_side*1}:{index_per_side*2 - 1}]", index_per_side))  
                # east_input_ports.append((f"{name}[{index_per_side*2}:{index_per_side*3 - 1}]", index_per_side))  
                # west_input_ports.append((f"{name}[{index_per_side*3}:{index_per_side*4 - 1}]", index_per_side))  
                
            # else:
                # if interface == 'axis' and 'axis' in name.lower():
                #     core_input_ports.append((name, size))
                # else:
                #     core_input_ports.append((name, size))

    for output_port in port_dict[top]["outputs"]:
        for name, size in output_port.items():
            if interface == 'axis' and 'axis' in name.lower():
                core_output_ports.append((name, size))
            elif 'top' in name.lower() or 'north' in name.lower():
                north_output_ports.append((name, size))
            elif 'right' in name.lower() or 'east' in name.lower():
                east_output_ports.append((name, size))
            elif 'bottom' in name.lower() or 'south' in name.lower():
                south_output_ports.append((name, size))
            elif 'left' in name.lower() or 'west' in name.lower():
                west_output_ports.append((name, size))
            else:
                directional_out_ports.append((name, size))


    for port, size in core_input_ports:
        if "data" in port.lower():
            data_size = size
    
    tile_size_y = (data_size + 9) // 10
    tile_size_x =  4
    tile_size = (tile_size_x, tile_size_y)
    
    

    # write vpr file
    vpr_tree = ET.parse(vpr_arch_file)
    vpr_root = vpr_tree.getroot()

    # print(f'Writing VPR arch file using template {vpr_arch} at {vpr_arch_file}')
    # add model tag
    add_vpr_model(top, 
                #   port_dict,
                # directional_in_ports, directional_out_ports,
                # north_input_ports, north_output_ports, east_input_ports, east_output_ports, south_input_ports, south_output_ports, west_input_ports, west_output_ports,
                  core_input_ports, core_output_ports, clock_reset_ports, 
                  has_clock, clock_port, vpr_arch_file, vpr_root, vpr_tree)
    # physical model
    all_input_ports = north_input_ports + east_input_ports + south_input_ports + west_input_ports + directional_in_ports + core_input_ports
    all_output_ports = north_output_ports + east_output_ports + south_output_ports + west_output_ports + directional_out_ports + core_output_ports
    add_vpr_model(f"{top}_physical", 
                #   port_dict,
                # directional_in_ports, directional_out_ports,
                # north_input_ports, north_output_ports, east_input_ports, east_output_ports, south_input_ports, south_output_ports, west_input_ports, west_output_ports,
                  all_input_ports, all_output_ports, clock_reset_ports, 
                  has_clock, clock_port, vpr_arch_file, vpr_root, vpr_tree)
    # add tile tag
    add_vpr_tile(top,
                #   port_dict,
                 directional_in_ports, directional_out_ports,
                 north_input_ports, north_output_ports, east_input_ports, east_output_ports, south_input_ports, south_output_ports, west_input_ports, west_output_ports, core_input_ports, core_output_ports, clock_reset_ports,
                 tile_size,
                 has_clock, clock_port, vpr_arch_file, vpr_root, vpr_tree)
 

    # add pb_type tag
    add_vpr_pb_type(top, 
                    # port_dict, 
                    # directional_ports,
                    directional_in_ports, directional_out_ports,
                    north_input_ports, north_output_ports, east_input_ports, east_output_ports, south_input_ports, south_output_ports, west_input_ports, west_output_ports, core_input_ports, core_output_ports, clock_reset_ports,
                    has_clock, clock_port, vpr_arch_file, vpr_root, vpr_tree)

    add_vpr_layout_tag(top, port_dict, has_clock, clock_port, vpr_arch_file, vpr_root, vpr_tree)

    add_vpr_noc_tag(top, vpr_arch_file, vpr_root, vpr_tree)
    # print(f"# Completed writing VPR arch file with '{top}' as a hard block")

    # write openfpga file
    openfpga_tree = ET.parse(openfpga_arch_file)
    openfpga_root = openfpga_tree.getroot()

    # print("-------- Writing openfpga arch file --------")
    # print(f'Writing OpenFPGA arch file using template {openfpga_arch} at {openfpga_arch_file}')

    add_openfpga_circuit_model(top, verilog_file, spice_file, port_dict, has_clock, clock_port, openfpga_arch_file, openfpga_root, openfpga_tree)
    add_openfpga_pb_type_annotation(top, openfpga_arch_file, openfpga_root, openfpga_tree)
    add_openfpga_noc_tag(top, 
                        #  port_dict,
                        directional_in_ports, directional_out_ports,
                        north_input_ports, north_output_ports, east_input_ports, east_output_ports, south_input_ports, south_output_ports, west_input_ports, west_output_ports,
                        core_input_ports, core_output_ports, clock_reset_ports,
                        openfpga_arch_file, openfpga_root, openfpga_tree)



