#!/bin/bash
#title           : openfpga.sh
#description     : This script provides shortcut commands <bash functions>
#                  for several simple operations in OpenFPGA project
#author          : Ganesh Gore <ganesh.gore@utah.edu>
#==============================================================================

if [ -z $OPENFPGA_PATH ]; then
    echo "OPENFPGA_PATH variable not found"
    export OPENFPGA_PATH=$(pwd);
    echo "Setting OPENFPGA_PATH=${OPENFPGA_PATH}"
else
    echo "OPENFPGA_PATH=${OPENFPGA_PATH}"
fi
export OPENFPGA_SCRIPT_PATH="${OPENFPGA_PATH}/openfpga_flow/scripts"
export OPENFPGA_TASK_PATH="${OPENFPGA_PATH}/openfpga_flow/tasks"
if [ -z $PYTHON_EXEC ]; then export PYTHON_EXEC="python3"; fi

# This function checks the path and
# raises warning if the command is not executing
# inside current OpendFPGA folder
check_execution_path (){
    if [[ $1 != *"${OPENFPGA_PATH}"* ]]; then
        echo -e "\e[33mCommand is not executed from configured OPENFPGA directory\e[0m"
    fi
}

run-task-with-modelsim () {
    echo "Script as to be run as \"run-task-with-modelsim task_name --maxthreads nb_threads other_run-modelsim_options\""
    $PYTHON_EXEC $OPENFPGA_SCRIPT_PATH/run_fpga_task.py $1 $2 $3
    $PYTHON_EXEC $OPENFPGA_SCRIPT_PATH/run_modelsim.py "$@"
}

create-task () {
    if [ -z $1 ]; then
        echo "requires task name create-task <task_name>"
        return
    fi
    if [ -d $1 ]; then
        echo "Task $1 already exists"
        return
    fi
    template="template_tasks/fabric_netlist_gen_template"
    if [ ${#2} -ge 1 ]; then
        if   [[ "$2" == "fabric_netlist_gen" ]]; then template="template_tasks/${2}_template/";
        elif [[ "$2" == "fabric_verification" ]]; then template="template_tasks/${2}_template/";
        elif [[ "$2" == "frac-lut-arch-explore" ]]; then template="template_tasks/${2}_template/";
        elif [[ "$2" == "vtr_benchmarks" ]]; then template="template_tasks/${2}_template/";
        else template="$2"
        fi
    fi
    if [ ! -f $OPENFPGA_PATH/openfpga_flow/tasks/${template}/config/task.conf ]; then
        echo "Template project [${template}] does not exist" ; return;
    fi
    echo "Creating task     $1"
    echo "Template project  ${template}"
    mkdir -p $1
    cp -r $OPENFPGA_PATH/openfpga_flow/tasks/${template}/* $1/
}

rerun-task () {
    $PYTHON_EXEC $OPENFPGA_SCRIPT_PATH/run_fpga_task.py "$@" --remove_run_dir all
    $PYTHON_EXEC $OPENFPGA_SCRIPT_PATH/run_fpga_task.py "$@"
}

run-task () {
    $PYTHON_EXEC $OPENFPGA_SCRIPT_PATH/run_fpga_task.py "$@"
}

clean-run () {
    rm -rf ./openfpga_flow/**/run???
}

clear-task-run () {
    $PYTHON_EXEC $OPENFPGA_SCRIPT_PATH/run_fpga_task.py "$@" --remove_run_dir all
}

run-modelsim () {
    $PYTHON_EXEC $OPENFPGA_SCRIPT_PATH/run_modelsim.py "$@"
}

run-flow () {
    $PYTHON_EXEC $OPENFPGA_SCRIPT_PATH/run_fpga_flow.py "$@"
}

# lists all the configure task in task directory
list-tasks () {
    echo "Repository Task"
    tree -P 'task.conf' --prune $OPENFPGA_TASK_PATH | sed "/.* task.conf/d" | sed "/.* config/d" | sed '$d'
    echo "Local Task"
    tree -P 'task.conf' --prune | sed "/.* task.conf/d" | sed "/.* config/d" | sed '$d'
}

# Switch directory to root of OpenFPGA
goto-root () {
    cd $OPENFPGA_PATH
}

# Run regression test locally
run-regression-local () {
    cd ${OPENFPGA_PATH}
    bash .github/workflows/*reg_test.sh
}

# Changes directory to task directory [goto_task <task_name> <run_num[default 0]>]
goto-task () {
    if [ -z $1 ]; then
        echo "requires task name goto_task <task_name> <run_num[default 0]>"
        return
    fi
    goto_path=$OPENFPGA_TASK_PATH/$1
    if [ -d $1 ]; then  goto_path=./$1; fi
    echo $goto_path
    # Selects the run directory
    run_num=""
    if [ ! -d $goto_path ]; then echo "Task directory not found"; return; fi
    if [[ "$2" =~ '^[0-9]+$' ]] ; then
        if ! [[ $2 == '0' ]] ; then run_num="$(printf run%03d $2)"; else run_num="latest"; fi
        if [ ! -d "$goto_path/$run_num" ]; then run_num="latest"; fi
    fi
    if [ ! -d $goto_path/$run_num ]; then
        echo "\e[33mTask run directory not found -" $goto_path/$run_num "\e[0m"
    else
        echo "Switching current dirctory to" $goto_path/$run_num
        cd $goto_path/$run_num
    fi
    # Selects benchmark directory
    select benchRun in $(ls -d **/arch | sed "s/\/arch//" | head -n 20)
    do
        [ -d ${benchRun} ] && cd ${benchRun}
        break
    done
}

# Clears environment variables and functions
unset-openfpga (){
    unset -v OPENFPGA_PATH
    unset -f list-tasks run-task run-flow goto-task goto-root >/dev/null 2>&1
}

# Allow autocompletion of task
if [[ $(ps -p $$ -oargs=) == *"zsh"* ]]; then
    autoload -U +X bashcompinit; bashcompinit;
fi

command -v shopt && shopt -s globstar
# TaskList=$(ls -tdalh ${OPENFPGA_TASK_PATH}/* | awk '{system("basename " $9)}' |  awk '{printf("%s ",$1)}')
RepoTaskList=$(ls -tdalh ${OPENFPGA_TASK_PATH}/**/task.conf  |
awk '{print $9}' | sed -e "s/\/config\/task.conf//" |
sed -e "s/${OPENFPGA_PATH//\//\\/}\/openfpga_flow\/tasks\///" |
awk '{printf("%s ",$1)}')

_TaskList()
{
  local cur
  COMPREPLY+=($( ls -R ./*/*/task.conf | sed -e "s/\/config\/task.conf//" | sed -e "s/^\.\///" | awk '{printf("%s ",$1)}' ) )
}

complete -W "${RepoTaskList}" -F _TaskList goto-task
complete -W "${RepoTaskList}" -F _TaskList run-task
complete -W "${RepoTaskList}" -F _TaskList run-modelsim
complete -W "${RepoTaskList}" create-task


# Push button flow
PBF_SCRIPT_PATH=${OPENFPGA_PATH}/openfpga_noc/pbf_scripts

# Function to set up run directory and change into it
setup-run-from-config() {
    if [ -z "$1" ]; then
        echo "Error: Please provide a task directory"
        echo "Usage: setup-run-from-config <task_directory>"
        return 1
    fi

    # Run the Python script and capture its output
    local output=$(python3 ${PBF_SCRIPT_PATH}/setup_run_dir_from_config.py -t "$1")
    
    # Extract the run directory path from the output
    # local run_dir=$(echo "$output" | grep -A 1 "Created  run dir" | tail -n 1 | xargs)
    local run_dir=$(echo "$output" | tail -n 1)
    
    if [ -d "$run_dir" ]; then
        echo "Changing directory to $run_dir"
        cd "$run_dir"
    else
        echo "Error: Failed to create run directory or directory doesn't exist"
        echo "Python script output:"
        echo "$output"
        return 1
    fi
    # Check if the directory change was successful
    if [ $? -ne 0 ]; then
        echo "Error: Failed to change directory to $run_dir"
        return 1
    else 
        echo "-- run dir setup successful --"
        echo "Use 'make' to run the tasks"
    fi

}

# Make the function available as a command
# alias setup-run-dir=setup_run_dir

setup-pbf-run() {
    # push_button_flows.py
    # requires 2 argumnts "-c" for yaml config file and "-t" for task run directory
    # if less than 2 args given, print usage
    if [ "$#" -lt 2 ]; then
        echo "Usage: setup-pbf-run -c <config_file.yaml> -t <task_run_directory>"
        return 1
    fi
    echo "Running Push Button Flow with arguments: $@"
    python3 ${PBF_SCRIPT_PATH}/push_button_flows.py "$@"
}
