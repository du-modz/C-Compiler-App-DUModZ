# app.py
import os
import subprocess
import tempfile
import re
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

DANGEROUS_FUNCTIONS = [
    r'\bsystem\s*\(',
    r'\bpopen\s*\(',
    r'\bexec\s*\(',
    r'\bfork\s*\(',
    r'\bkilled\s*',
    r'\bchmod\s*\(',
    r'\brm\s+-rf',
]

def is_dangerous(code):
    for pattern in DANGEROUS_FUNCTIONS:
        if re.search(pattern, code, re.IGNORECASE):
            return True
    return False

def requires_input(code):
    # Check if scanf, gets, fgets etc. are used
    patterns = [r'\bscanf\s*\(', r'\bgets\s*\(', r'\bfgets\s*\(']
    for p in patterns:
        if re.search(p, code):
            return True
    return False

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/compile', methods=['POST'])
def compile_code():
    data = request.json
    code = data.get('code', '').strip()
    user_input = data.get('input', '').strip()

    if not code:
        return jsonify({'error': 'কোড খালি রাখা যাবে না!'}), 400

    if is_dangerous(code):
        return jsonify({
            'error': '⚠️ আপনার কোডে অনিরাপদ ফাংশন (যেমন: system, popen) ব্যবহার করা হয়েছে! এটি অনুমোদিত নয়।'
        }), 400

    needs_input = requires_input(code)
    if needs_input and not user_input.strip():
        return jsonify({
            'error': '🔴 আপনার কোডে <code>scanf</code>, <code>gets</code> বা অনুরূপ ইনপুট ফাংশন আছে। অবশ্যই "scanf value input" ট্যাবে ইনপুট দিন!'
        }), 400

    with tempfile.TemporaryDirectory() as tmpdir:
        c_file = os.path.join(tmpdir, 'program.c')
        exe_file = os.path.join(tmpdir, 'program')

        with open(c_file, 'w') as f:
            f.write(code)

        # Compile
        try:
            compile_result = subprocess.run(
                ['gcc', c_file, '-o', exe_file, '-Wall', '-Wextra'],
                capture_output=True,
                text=True,
                timeout=10
            )
            if compile_result.returncode != 0:
                return jsonify({'error': f'❌ কম্পাইল এরর:\n{compile_result.stderr}'}), 400
        except subprocess.TimeoutExpired:
            return jsonify({'error': '⏰ কম্পাইলেশন টাইমআউট!'}), 400

        # Run
        try:
            run_result = subprocess.run(
                [exe_file],
                input=user_input,
                capture_output=True,
                text=True,
                timeout=5,
                cwd=tmpdir
            )
            output = run_result.stdout
            error = run_result.stderr
            if run_result.returncode != 0:
                output += f"\n[Exit Code: {run_result.returncode}]"
            if error:
                output += f"\nstderr: {error}"
            return jsonify({'output': output})
        except subprocess.TimeoutExpired:
            return jsonify({'error': '⏰ প্রোগ্রাম রান করতে টাইমআউট! (5s এর বেশি সময় নেওয়া যাবে না)'}), 400
        except Exception as e:
            return jsonify({'error': f'রানটাইম এরর: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
