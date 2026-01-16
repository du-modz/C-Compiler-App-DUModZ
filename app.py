import subprocess
import os
import uuid
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/run', methods=['POST'])
def run_code():
    code = request.form.get('code', '')
    user_input = request.form.get('input', '')
    
    # সিকিউরিটি এবং scanf চেক
    if "scanf" in code and not user_input.strip():
        return jsonify({
            "output": "Error: আপনি কোডে scanf ব্যবহার করেছেন কিন্তু কোনো Input Value দেননি! দয়া করে 'Scanf Value Input' ট্যাবে ইনপুট দিন।",
            "status": "error"
        })

    filename = f"temp_{uuid.uuid4().hex}"
    c_file = f"{filename}.c"
    exe_file = f"{filename}.out"

    with open(c_file, "w") as f:
        f.write(code)

    try:
        # কম্পাইল করা
        compile_process = subprocess.run(
            ["gcc", c_file, "-o", exe_file],
            capture_output=True, text=True
        )
        
        if compile_process.returncode != 0:
            return jsonify({"output": compile_process.stderr, "status": "error"})

        # রান করা (৫ সেকেন্ড টাইমআউট সিকিউরিটি)
        run_process = subprocess.run(
            [f"./{exe_file}"],
            input=user_input,
            capture_output=True,
            text=True,
            timeout=5
        )
        output = run_process.stdout + run_process.stderr
        return jsonify({"output": output, "status": "success"})

    except subprocess.TimeoutExpired:
        return jsonify({"output": "Error: Execution Timeout! (অসীম লুপ হতে পারে)", "status": "error"})
    except Exception as e:
        return jsonify({"output": str(e), "status": "error"})
    finally:
        # ফাইল ডিলিট করা
        if os.path.exists(c_file): os.remove(c_file)
        if os.path.exists(exe_file): os.remove(exe_file)

if __name__ == '__main__':
    app.run(debug=True)
