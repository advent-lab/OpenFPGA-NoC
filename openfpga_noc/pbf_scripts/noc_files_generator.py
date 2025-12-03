import re






    # gen_router_rtl(router_rtl, router_blackbox, yaml_config["fabric_gen_config"]["router"])
def gen_router_rtl(router_rtl, router_blackbox, rtr_wrap_template, rtr_wrap_blackbox_template, router_config):

    default_parameters = {
        "NUM_PORTS" : 5,
        "NOC_NUM_ENDPOINTS" : 16,
        "FLIT_BUFFER_DEPTH" : 8,
        "SERDES_BUFFER_DEPTH" : 8,
        "TID_WIDTH" : 2,
        "TDEST_WIDTH" : 4,
        "TDATA_WIDTH" : 128,
        "SERIALIZATION_FACTOR" : 2,
        "CLKCROSS_FACTOR" : 1,
        "SINGLE_CLOCK" : 1,
        "RESET_SYNC_EXTEND_CYCLES" : 2,
        "RESET_NUM_OUTPUT_REGISTERS" : 1,
        "SERDES_IN_BUFFER_DEPTH" : "SERDES_BUFFER_DEPTH",
        "SERDES_OUT_BUFFER_DEPTH" : "SERDES_BUFFER_DEPTH",
        "SERDES_EXTRA_SYNC_STAGES" : 0,
        "SERDES_FORCE_MLAB" : 0,
        "ROUTING_TABLE_HEX" : "routing_tables/router_4x4/",
        "ROUTER_PIPELINE_ROUTE_COMPUTE" : 1,
        "ROUTER_PIPELINE_ARBITER" : 1,
        "ROUTER_PIPELINE_OUTPUT" : 1,
        "ROUTER_FORCE_MLAB" : 0,
        "FLIT_WIDTH" : "TDATA_WIDTH / SERIALIZATION_FACTOR / CLKCROSS_FACTOR",
        "DEST_WIDTH" : 4,
        "RTR_ADDR_WIDTH" : 4,
        "ROUTE_WIDTH" : 3,
        "NUM_PIPELINE" : 0
    }

    # Update parameters with values from config
    parameters = {
        "TDATA_WIDTH" : router_config["interface_width"],
        "SERDES_BUFFER_DEPTH" : router_config["interface_buffer_depth"],
        "FLIT_BUFFER_DEPTH" : router_config["flit_buffer_depth"],
        "SERIALIZATION_FACTOR" : router_config["interface_width"] // router_config["flit_width"],
    }


    # Read the template
    with open(rtr_wrap_template, 'r') as f:
        template_content = f.read()
    # Replace parameters in the template
    for param_name, param_value in parameters.items():
        placeholder = f"parameter {param_name} = {default_parameters[param_name]},"
        replacement = f"parameter {param_name} = {param_value},"
        template_content = re.sub(placeholder, replacement, template_content)
    
    # Write the output RTL file
    with open(router_rtl, 'w') as f:
        f.write(template_content)

    with open(rtr_wrap_blackbox_template, 'r') as f:
        template_content = f.read()
    # Replace parameters in the template
    for param_name, param_value in parameters.items():
        placeholder = f"parameter {param_name} = {default_parameters[param_name]},"
        replacement = f"parameter {param_name} = {param_value},"
        template_content = re.sub(placeholder, replacement, template_content)
    
    # Write the output RTL file
    with open(router_blackbox, 'w') as f:
        f.write(template_content)

    return router_rtl, router_blackbox


def gen_noc_bench(template, bench, dataw=128, destw=4):
# T_DATAW = 128
# T_DESTW = 4
    with open(template, 'r') as f:
        template_content = f.read()
    # Replace parameters in the template
    placeholder1 = "T_DATAW = 128,"
    replacement1 = f"T_DATAW = {dataw},"
    template_content = re.sub(placeholder1, replacement1, template_content)

    placeholder2 = "T_DESTW = 4"
    replacement2 = f"T_DESTW = {destw}"
    template_content = re.sub(placeholder2, replacement2, template_content)

    # Write the output RTL file
    with open(bench, 'w') as f:
        f.write(template_content)


if __name__ == "__main__":
    gen_router_rtl(
        router_rtl="/mnt/vault1/rsunketa/OpenFPGA/openfpga_noc/pbf_scripts/test/router_wrap.v",
        router_blackbox="/mnt/vault1/rsunketa/OpenFPGA/openfpga_noc/pbf_scripts/test/router_blackbox.v",
        rtr_wrap_template="/mnt/vault1/rsunketa/OpenFPGA/openfpga_noc/pbf_scripts/templates/router_wrap.sv",
        rtr_wrap_blackbox_template="/mnt/vault1/rsunketa/OpenFPGA/openfpga_noc/pbf_scripts/templates/router_wrap_cell_sim.sv",
        router_config={}
    )

