Step 1: Activate your virtual environment

If your folder has a venv/ directory (it does), activate it first.

🪟 On Windows:
venv\Scripts\activate

🐧 On macOS/Linux:
source venv/bin/activate


Once activated, your terminal prompt should show something like:

(venv) C:\Users\You\REALAPEX>

🧩 Step 2: Install all dependencies

Use your requirements.txt file to install all needed packages:

pip install -r requirements.txt


This ensures your environment has everything (e.g., Flask, requests, etc.).

⚙️ Step 3: Identify the main file

Your entry file is likely main.py (it’s common convention).
Open main.py and check for something like:

if __name__ == "__main__":
    app.run()


or

asyncio.run(main())


If you see one of these, that’s your starting point.

🚀 Step 4: Run the project

In the terminal (with the venv activated):

python main.py


or if it’s using uvicorn (like FastAPI):

uvicorn main:app --reload

✅ Step 5: Check logs/output

Once it runs, you’ll see something like:

Running on http://127.0.0.1:8000


Then open that link in your browser to test the app.