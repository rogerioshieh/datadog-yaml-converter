from flask import Flask, render_template, request
import yaml
import json
import re

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html", output_text="your_text_here")


@app.route("/convert", methods=["POST"])
def convert():
    
    try:
        text = yaml.safe_load(request.form['input_text'])  
        extra_text = yaml.safe_load(request.form['extra_input_text'])  
    except Exception:
        return "ERROR:\n\nYaml not in valid format, try again."

    # make empty string if no config available
    check_name = "CHECK_NAME" if not request.form['check_name'] else request.form['check_name'].lower()
    container_id = "CONTAINER_IDENTIFIER" if request.form['container_id'] == "" else request.form['container_id'].lower()
    
    init_config = "" if not text.get('init_config') else text['init_config']
    init_config = "{" + init_config + "}"
    
    instances = "" if not text.get('instances') else str(text['instances']).replace("'", "\"")
    logs = "" if not text.get('logs') else str(text['logs']).replace("'", "\"")

    #process more than one check
    extra_check_name = request.form['extra_check_name']
    print(len(extra_check_name))
    print(len(extra_text))
    if extra_check_name != "undefined" or extra_text != "undefined":
        
        extra_check_name = "CHECK_NAME2" if not extra_check_name else extra_check_name
        checks = [check_name, extra_check_name]
        check_name = str(checks).replace("[", "").replace("]", "").replace("'", "\"")

        extra_init_config = "" if not extra_text.get('init_config') else extra_text['init_config']
        extra_init_config = "{" + extra_init_config + "}"
        init_configs = [init_config, extra_init_config]
        init_config = str(init_configs).replace("[", "").replace("]", "").replace(" ", "").replace("\'", "")

        extra_instance = "" if not text.get('instances') else str(extra_text['instances']).replace("'", "\"")
        all_instances = [instances, extra_instance]
        instances = str(all_instances).replace("'", "")

    else:
        check_name = "\"" + check_name + "\""
    
    if request.form['req_type'] != "kubernetes":
        return convert_docker(init_config, instances, logs, check_name, request.form['req_type'])
    else:
        return convert_kubernetes(init_config, instances, logs, check_name, container_id)


def convert_docker(init_config, instances, logs, check_name, output_type):

    # for docker, the extra space is not necessary
    instances = instances.replace(" ", "")
    logs = logs.replace(" ", "")

    if output_type == "dockerfile":
        label, delimiter = "LABEL ", "="
    elif output_type == "docker_run":
        label, delimiter = "-l ", "="
    else:
        label, delimiter = "", ": "

    final_string = (
        f"{label}com.datadoghq.ad.check_names{delimiter}'[{check_name}]'\n"
        f"{label}com.datadoghq.ad.init_configs{delimiter}'[{init_config}]'\n"
        f"{label}com.datadoghq.ad.instances{delimiter}'{instances}'"
    )

    #this is necessary otherwise Python will print escape characters as // instead of / 
    decoded_string = bytes(logs, "utf-8").decode("unicode_escape")
    logs_label = f"\n{label}com.datadoghq.ad.instances{delimiter}'{decoded_string}'"

    #omit logs label if not present
    return final_string + logs_label if logs else final_string


def convert_kubernetes(init_config, instances, logs, check_name, container_id):

    final_string_beg =  (
        "metadata\n"
        "  name: 'POD_NAME'\n  "
        "  annotations:\n  "
        f"    ad.datadoghq.com/{container_id}.check_names: '[\"{check_name}\"]'\n  "
        f"    ad.datadoghq.com/{container_id}.init_configs: '[{init_config}]'\n  "
        f"    ad.datadoghq.com/{container_id}.instances: '{instances}'"
    )

    logs_label = f"\n      ad.datadoghq.com/{container_id}.logs: '{logs}'\n  "

    final_string_end = (
        "    # (...)\n"
        "spec:\n  "
        "containers:\n  "
        f"  - name: '{container_id}'\n"
        "# (...)"
    )

    #omit logs annotation if not present
    return final_string_beg + logs_label + final_string_end if logs else final_string_beg + final_string_end


if __name__ == '__main__':
    app.run(debug=True,host='0.0.0.0')