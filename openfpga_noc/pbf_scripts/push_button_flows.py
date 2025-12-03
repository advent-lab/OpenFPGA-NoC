import os
import shutil
import yaml
import argparse
from types import SimpleNamespace

from arch_file_generator import generate_arch_files 
from task_config_file_generator import gen_task_config
from noc_files_generator import gen_router_rtl, gen_noc_bench


# Function to parse command line arguments
# def parse_args():
#     parser = argparse.ArgumentParser(description="Process YAML configuration for OpenFPGA NoC.")
#     parser.add_argument("--config", '-c', type=str, required=True, help="Path to the YAML configuration file")
#     parser.add_argument("--task_dir", '-t', type=str, required=True, help="Directory for the task")
#     return parser.parse_args()
def parse_args():
    parser = argparse.ArgumentParser(description="Process YAML configuration for OpenFPGA NoC.")
    parser.add_argument("--config", '-c', type=str, required=True, help="Path to the YAML configuration file")
    parser.add_argument("--task_dir", '-t', type=str, required=True, help="Directory for the task")
    args = parser.parse_args()
    args.config = os.path.abspath(args.config)
    args.task_dir = os.path.abspath(args.task_dir)
    return args

# def create_pbf_dir(task_dir):
#     # creates a main push button flow dir:
#     # # first it

def create_collateral_dir(task_dir, yaml_config):
    # creates a collateral dir inside the task dir
    collateral_dir = f"{task_dir}/collateral"
    if not os.path.exists(collateral_dir):
        os.makedirs(collateral_dir)
    arch_dir = os.path.join(collateral_dir, "arch")
    if not os.path.exists(arch_dir):
        os.makedirs(arch_dir)
    fabric_collateral = os.path.join(collateral_dir, "fabric_collateral")
    if not os.path.exists(fabric_collateral):
        os.makedirs(fabric_collateral)
    vpr_collateral = os.path.join(collateral_dir, "vpr_collateral")
    if not os.path.exists(vpr_collateral):
        os.makedirs(vpr_collateral)
    router_models = os.path.join(collateral_dir, "router_models")
    if not os.path.exists(router_models):
        os.makedirs(router_models)

    print(f"Collateral directories created at: {collateral_dir}")
    print("----------------------------")
    rtr_wrap_template = os.path.join(os.getenv('OPENFPGA_PATH'), "openfpga_noc/pbf_scripts/templates/router_wrap.sv")
    rtr_wrap_blackbox_template = os.path.join(os.getenv('OPENFPGA_PATH'), "openfpga_noc/pbf_scripts/templates/router_wrap_cell_sim.sv")

    # create router rtl collateral
    router_rtl = os.path.join(router_models, "router_wrap.sv")
    router_blackbox = os.path.join(router_models, "router_wrap_blackbox.sv")
    # gen_router_rtl(router_rtl, router_blackbox, yaml_config["fabric_gen_config"]["router"])
    gen_router_rtl(
        router_rtl,
        router_blackbox,
        rtr_wrap_template,
        rtr_wrap_blackbox_template,
        yaml_config["fabric_gen_config"]["router"]
    )
    print(f"Router RTL files created at: {router_rtl} and {router_blackbox}")

    # create arch files
    vpr_baseline = yaml_config["fabric_gen_config"]["FPGA"]["vpr"]
    openfpga_baseline = yaml_config["fabric_gen_config"]["FPGA"]["openfpga"]

    vpr_arch_file = os.path.join(arch_dir, "vpr_arch.xml")
    openfpga_arch_file = os.path.join(arch_dir, "openfpga_arch.xml")
    # gen_vpr_arch_file(vpr_arch_gen_args)
    # gen_openfpga_arch_file(openfpga_arch_gen_args)


# def generate_arch_files(yosys_path, verilog_file, spice_file, top, output_dir, vpr_arch, openfpga_arch, is_noc):
# def generate_arch_files(name, yosys_path, verilog_file, spice_file, top, vpr_output_dir, openpfga_output_dir, temp_dir, vpr_arch, openfpga_arch):
    generate_arch_files(
        "/mnt/vault1/rsunketa/OpenFPGA/build/yosys/bin/yosys", # yosys_path
        router_blackbox,
        router_blackbox, # spice_file
        "router_wrap", # top
        arch_dir, # output_dir
        vpr_baseline, # vpr_arch
        openfpga_baseline, # openfpga_arch
        is_noc=True # is_noc
    )

# def generate_arch_files(yosys_path, verilog_file, spice_file, top, output_dir, vpr_arch, openfpga_arch, is_noc):


    print(f"Architecture files generated at: {collateral_dir}")
    print(f"VPR architecture file created at: {vpr_arch_file}")
    print(f"OpenFPGA architecture file created at: {openfpga_arch_file}") 
    return collateral_dir

def create_fabric_gen_dir(task_dir, yaml_config):
    # creates a fabric gen dir inside the task dir
    fabric_gen_dir = os.path.join(task_dir, "fabric")
    # vpr_arch_file = f"{task_dir}/collateral/vpr_arch.xml"
    vpr_arch_file = os.path.join(task_dir, "collateral/arch/vpr_arch.xml")
    openfpga_arch_file = os.path.join(task_dir, "collateral/arch/openfpga_arch.xml")
    fabric_gen_shell_script = os.path.join(os.getenv('OPENFPGA_PATH'), "openfpga_noc/pbf_scripts/templates/fabric_gen_shell_script.openfpga")

    if not os.path.exists(fabric_gen_dir):
        os.makedirs(fabric_gen_dir)
        os.makedirs(os.path.join(fabric_gen_dir, "config"))
    # create the fabric gen task config file
    fabric_gen_config_file = os.path.join(fabric_gen_dir, "config/task.conf")
    # gen_fabric_task_config(fabric_gen_config_file, yaml_config["fabric_gen_config"])
        # def gen_task_config(config_file, OPENFPGA_PATH, shell_script, openfpga_arch, vpr_arch, bench, bench_top):
    fabric_gen_bench_template = os.path.join(os.getenv('OPENFPGA_PATH'), "openfpga_noc/pbf_scripts/templates/noc_bench.v")
    fabric_gen_bench = os.path.join(fabric_gen_dir, "noc_bench.v")

    router_blackbox = os.path.join(task_dir, "collateral/router_models/router_wrap_blackbox.sv")

    traffic_flows_source = os.path.join(os.getenv('OPENFPGA_PATH'), "openfpga_noc/pbf_scripts/templates/traffic.flows")
    # coopy to current dir
    traffic_flows = os.path.join(fabric_gen_dir, "traffic.flows")
    shutil.copy(traffic_flows_source, traffic_flows)

# def gen_noc_bench(template, bench, dataw=128, destw=4):
    gen_noc_bench(fabric_gen_bench_template, fabric_gen_bench, yaml_config["fabric_gen_config"]["router"]["interface_width"], yaml_config["fabric_gen_config"]["NoC"]["num_routers"].bit_length())
    gen_task_config(fabric_gen_config_file, os.getenv("OPENFPGA_PATH"), fabric_gen_shell_script, openfpga_arch_file, vpr_arch_file, fabric_gen_bench, "noc_bench_top", traffic_flows, router_blackbox)

    print(f"Fabric generation config file created at: {fabric_gen_config_file}")

def create_bitstream_gen_dir(task_dir, yaml_config):
    # creates a bitstream gen dir inside the task dir
    bitstream_gen_dir = os.path.join(task_dir, "bitstream")
    vpr_arch_file = os.path.join(task_dir, "collateral/arch/vpr_arch.xml")
    openfpga_arch_file = os.path.join(task_dir, "collateral/arch/openfpga_arch.xml")

    bench = yaml_config["bitstream_gen_config"]["design"]
    bench_top = yaml_config["bitstream_gen_config"]["top"]
    traffic_flows = yaml_config["bitstream_gen_config"]["traffic_model"]

    # if bench is not valid file
    if not os.path.isfile(bench):
        print(f"Bench file {bench} not found in the specified path. Using default noc_bench.v")
        bench = os.path.join(task_dir, "fabric", "noc_bench.v")
        bench_top = "noc_bench_top"
        traffic_flows = os.path.join(task_dir, "fabric", "traffic.flows")


    bitstream_gen_shell_script = os.path.join(os.getenv('OPENFPGA_PATH'), "openfpga_noc/pbf_scripts/templates/bitstream_gen_shell_script.openfpga")



    if not os.path.exists(bitstream_gen_dir):
        os.makedirs(bitstream_gen_dir)
        os.makedirs(os.path.join(bitstream_gen_dir, "config"))
    # create the bitstream gen task config file
    bitstream_gen_config_file = os.path.join(bitstream_gen_dir, "config/task.conf")

    router_blackbox = os.path.join(task_dir, "collateral/router_models/router_wrap_blackbox.sv")
    # gen_bitstream_task_config(bitstream_gen_config_file, yaml_config["bitstream_gen_config"])
    gen_task_config(bitstream_gen_config_file, os.getenv("OPENFPGA_PATH"), bitstream_gen_shell_script, openfpga_arch_file, vpr_arch_file, bench, bench_top, traffic_flows, router_blackbox)

    print(f"Bitstream generation config file created at: {bitstream_gen_config_file}")


def main(args):
    # Load the YAML configuration file
    # with open("/mnt/vault1/rsunketa/OpenFPGA/openfpga_noc/pbf_scripts/test/sapmle.yaml", "r") as f:
    with open(args.config, "r") as f:
        yaml_config = yaml.safe_load(f)

    # Access values from the configuration
    # print(yaml_config["fabric_gen_config"]["NoC"]["num_routers"])
    # print(yaml_config["bitstream_gen_config"]["noc"]["routing_mode"])
    # print(yaml_config["bitstream_gen_config"]["noc"]["noc_freq_factor"])

    task_dir = args.task_dir
    print(f"Using task directory: {task_dir}")
    if not os.path.exists(task_dir):
        os.makedirs(task_dir)

    collateral_dir = create_collateral_dir(task_dir, yaml_config)
    print(f"Collateral directory created at: {collateral_dir}")


    create_fabric_gen_dir(task_dir, yaml_config)
    print(f"Fabric generation directory created at: {task_dir}/fabric")
    
    create_bitstream_gen_dir(task_dir, yaml_config)
    print(f"Bitstream generation directory created at: {task_dir}/bitstream")
    print("----------------------------------------------------------")

    print("------ Push button flow setup completed successfully ------")
    print(f"Use 'run-task {task_dir}/fabric' to generate the fabric netlists")
    print(f"Use 'run-task {task_dir}/bitstream' to generate the bitstream")
    print("----------------------------------------------------------")

if __name__ == "__main__":
    args = parse_args()
    main(args)