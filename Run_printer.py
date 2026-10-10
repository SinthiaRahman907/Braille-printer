import sys, os
from stepper_control import BraillePrinter
from braille_logic import print_braille_text

def print_from_text(printer, text):
    printer.wait_for_paper()
    print_braille_text(printer, text)
    print("[printer] Done.")

if __name__ == "__main__":
    printer = BraillePrinter()
    args = sys.argv[1:]

    if not args:
        # interactive prompt
        txt = input("Enter text (or blank to exit): ").strip()
        if not txt:
            sys.exit(0)
        print_from_text(printer, txt)

    elif args[0] in ("-w","--web"):
        # launch web UI
        import web_interface
        print("[printer] Starting web UI on port 5000…")
        web_interface.app.run(host="0.0.0.0", port=5000)

    else:
        # print from file or command-line args
        path = args[0]
        if os.path.exists(path):
            with open(path) as f:
                txt = f.read()
        else:
            txt = " ".join(args)
        if txt.strip():
            print_from_text(printer, txt)
        else:
            print("[printer] No text to print.")
