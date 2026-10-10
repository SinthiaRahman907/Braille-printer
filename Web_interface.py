
from flask import Flask, request, render_template_string
import threading
from stepper_control import BraillePrinter
from braille_logic import print_braille_text

app = Flask(__name__)
printer = BraillePrinter()

HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Braille Printer</title>
  <style>
    body { font-family: sans-serif; max-width: 600px; margin: 2rem auto; }
    h2 { color: #333; }
    textarea { width: 100%; font-size: 1rem; }
    button { padding: 0.5rem 1rem; font-size: 1rem; }
    .msg { margin-bottom: 1rem; color: green; }
  </style>
</head>
<body>
  <h2>Braille Printer Interface</h2>
  {% if msg %}
    <div class="msg"><strong>{{ msg }}</strong></div>
  {% endif %}
  <form method="post">
    <textarea name="text" rows="6" placeholder="Type your text here…"></textarea><br><br>
    <button type="submit">Print</button>
  </form>
</body>
</html>
"""

@app.route("/", methods=["GET","POST"])
def index():
    if request.method == "POST":
        txt = request.form.get("text","").strip()
        if not txt:
            return render_template_string(HTML, msg="Please enter some text.")
        def job():
            printer.wait_for_paper()
            print_braille_text(printer, txt)
        threading.Thread(target=job, daemon=True).start()
        return render_template_string(HTML, msg="Printing started… please wait.")
    return render_template_string(HTML, msg=None)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
