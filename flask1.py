enter this code their:
# ----- Core Libraries -----
import os
import pandas as pd
from datetime import datetime
import matplotlib

matplotlib.use('Agg')  # Add these two lines
import matplotlib.pyplot as plt

# ----- Web Framework -----
from flask import Flask, send_file, jsonify
from flask_cors import CORS

# ----- External Services / Data -----
from supabase import create_client, Client
# from deep_translator import GoogleTranslator # Not used in the provided snippet, but keep if needed elsewhere

# ----- PDF Generation -----
from fpdf import FPDF

# ----- Flask App Setup -----
app = Flask(_name_)
CORS(app) # Allows requests from web pages hosted on different origins

# ----- Configuration -----
# Assume data files are in the same directory as the script
BASE_PATH = "./"
MAIN_NUTRITION_FILE = "Modified_Nutrition_Data_No_Beverages.xlsx"
BEV_NUTRITION_FILE = "Beverages_Nutrition_Data.xlsx"
TEMP_PLOT_DIR = "temp_plots" # Directory to store temporary plot images

# --- Supabase Setup ---
# WARNING: Storing credentials directly in code is insecure for production.
# Consider using environment variables or a config file.
SUPABASE_URL = "https://mamdsaakoanrzkfcjojf.supabase.co"

SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1hbWRzYWFrb2FucnprZmNqb2pmIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0Mzg0ODQ3OSwiZXhwIjoyMDU5NDI0NDc5fQ.TmamnukGpVMjnLCYn4_52FXWc3JcLLV1tmK6Huh4sDQ"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    print(f"Error initializing Supabase client: {e}")
    print("Please ensure SUPABASE_URL and SUPABASE_KEY are set correctly.")
    # You might want to exit or handle this more gracefully depending on your needs
    supabase = None

# --- Static Data (Example) ---
# Replace with actual logic if needed, e.g., fetching from request arguments
student_id_to_process = "b053059a-abd8-434c-b536-73585f4dd57e" # Example student ID

# ----- Data Loading -----
logo_path = os.path.join(BASE_PATH, "logo.png") # Assuming logo.png in the same directory
main_nutrition_path = os.path.join(BASE_PATH, MAIN_NUTRITION_FILE)
bev_nutrition_path = os.path.join(BASE_PATH, BEV_NUTRITION_FILE)

try:
    main_df = pd.read_excel(main_nutrition_path)
    bev_df = pd.read_excel(bev_nutrition_path)
    nutrition_df = pd.concat([main_df, bev_df], ignore_index=True)
    print("Nutrition data loaded successfully.")
except FileNotFoundError:
    print(f"Error: One or more data files not found in '{BASE_PATH}'")
    print(f"Ensure '{MAIN_NUTRITION_FILE}' and '{BEV_NUTRITION_FILE}' exist.")
    # Exit or handle appropriately
    exit()
except Exception as e:
    print(f"Error loading nutrition data: {e}")
    # Exit or handle appropriately
    exit()

if not os.path.exists(logo_path):
    print(f"Warning: Logo file not found at '{logo_path}'. PDF may generate without a logo.")


# ----- Helper Functions -----

def fetch_student_data(student_id):
    """Fetch student data from Supabase"""
    if not supabase:
        print("Supabase client not initialized. Cannot fetch student data.")
        return None
    try:
        response = supabase.table("students").select("*").eq("id", student_id).execute()
        if response.data:
            return response.data[0]
        else:
            print(f"No data found for student ID: {student_id}")
            return None
    except Exception as e:
        print(f"Error fetching student data from Supabase: {e}")
        return None

def calculate_daily_needs(weight, height, age, gender):
    """Calculate daily nutritional needs (BMR and TDEE)."""
    try:
        # Basic validation
        if not all([isinstance(val, (int, float)) and val > 0 for val in [weight, height, age]]):
             raise ValueError("Weight, height, and age must be positive numbers.")
        if height > 3: # Basic check if height is likely in meters vs cm
            print("Warning: Height seems large (>3). Ensure it's in meters.")

        bmi = weight / (height ** 2)

        # Calculate BMR (Harris-Benedict equation - revised)
        if gender.lower() == "male":
            bmr = 88.362 + (13.397 * weight) + (4.799 * height * 100) - (5.677 * age)
        elif gender.lower() == "female":
            bmr = 447.593 + (9.247 * weight) + (3.098 * height * 100) - (4.330 * age)
        else:
            # Use an average if gender is not specified or different
             bmr_male = 88.362 + (13.397 * weight) + (4.799 * height * 100) - (5.677 * age)
             bmr_female = 447.593 + (9.247 * weight) + (3.098 * height * 100) - (4.330 * age)
             bmr = (bmr_male + bmr_female) / 2
             print(f"Gender '{gender}' not recognized as 'male' or 'female'. Using an average BMR.")

        # Estimate TDEE using a simplified activity multiplier
        # These multipliers are very general. Consider a more nuanced approach.
        # 1.2: Sedentary (little to no exercise)
        # 1.375: Lightly active (light exercise/sports 1-3 days/week)
        # 1.55: Moderately active (moderate exercise/sports 3-5 days/week)
        # 1.725: Very active (hard exercise/sports 6-7 days a week)
        # 1.9: Extra active (very hard exercise/sports & physical job)
        # Using a placeholder average multiplier here. Adjust as needed.
        activity_multiplier = 1.4 # Example: moderately active average
        tdee = bmr * activity_multiplier

        # Recommended Protein: 0.8g-1.2g per kg body weight is common. Using 1.0g/kg as an example.
        protein_needs = 1.0 * weight

        # Recommended Fats: Often 20-35% of total calories. Using 30% as an example.
        # 1 gram of fat = 9 calories.
        fat_needs = (0.30 * tdee) / 9

        # Recommended Fibre: General recommendations vary. Using example values.
        fibre_needs = 25 if age >= 10 else 20 # Simplified example

        return {
            "bmi": round(bmi, 2),
            "calories": round(tdee),
            "protein": round(protein_needs),
            "fats": round(fat_needs),
            "fibre": round(fibre_needs)
        }
    except Exception as e:
        print(f"Error calculating daily needs: {e}")
        # Return default/zero values or raise the exception
        return {"bmi": 0, "calories": 0, "protein": 0, "fats": 0, "fibre": 0}


def fetch_weekly_nutrition(student_id):
    """Fetch weekly food intake data from Supabase"""
    if not supabase:
        print("Supabase client not initialized. Cannot fetch weekly nutrition.")
        return pd.DataFrame() # Return empty DataFrame
    try:
        response = supabase.table("food_intake").select("*").eq("student_id", student_id).execute()
        if response.data:
             # Convert to DataFrame after checking if data exists
             df = pd.DataFrame(response.data)
             # Basic data cleaning/type conversion (add more as needed)
             if 'created_at' in df.columns:
                 df['created_at'] = pd.to_datetime(df['created_at'])
             # Convert numeric columns if they are not already
             for col in ['calories', 'protein', 'fats', 'fibre']: # Adjust column names if different
                 if col in df.columns:
                     df[col] = pd.to_numeric(df[col], errors='coerce')
             return df
        else:
             print(f"No food intake data found for student ID: {student_id}")
             return pd.DataFrame() # Return empty DataFrame
    except Exception as e:
        print(f"Error fetching weekly nutrition data from Supabase: {e}")
        return pd.DataFrame() # Return empty DataFrame on error

def aggregate_daily_intake(weekly_data_df):
    """Aggregates raw intake data into daily summaries."""
    if weekly_data_df.empty or 'created_at' not in weekly_data_df.columns:
        print("Weekly data is empty or missing 'created_at' column. Cannot aggregate.")
        # Return an empty DF with expected structure or handle differently
        return pd.DataFrame(columns=['Day', 'Calories_Consumed', 'Protein_Consumed', 'Fats_Consumed', 'Fibre_Consumed'])

    # Ensure 'created_at' is datetime
    weekly_data_df['created_at'] = pd.to_datetime(weekly_data_df['created_at'])

    # Extract day of the week
    weekly_data_df['Day'] = weekly_data_df['created_at'].dt.strftime('%A') # Gets 'Monday', 'Tuesday', etc.

    # Define nutrient columns to sum (adjust if your column names are different)
    nutrient_cols = ['calories', 'protein', 'fats', 'fibre']
    # Rename columns for clarity in the result
    rename_map = {col: f"{col.capitalize()}_Consumed" for col in nutrient_cols}

    # Group by day and sum the nutrients
    daily_summary = weekly_data_df.groupby('Day')[nutrient_cols].sum().reset_index()
    daily_summary = daily_summary.rename(columns=rename_map)

    # Ensure all days of the week are present, even if no data exists for some
    all_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    daily_summary = daily_summary.set_index('Day').reindex(all_days, fill_value=0).reset_index()

    return daily_summary


def generate_plots(df, output_dir="."):
    """Generate nutrition plots for the week and a summary table image."""
    plots = {}
    nutrients_to_plot = ["Calories", "Protein", "Fats", "Fibre"]

    # Ensure the output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Define colors for consistency
    color_needed = '#2ecc71'  # Green
    color_consumed = '#e74c3c' # Red

    for nutrient in nutrients_to_plot:
        needed_col = f"{nutrient}_Needed"
        consumed_col = f"{nutrient}_Consumed"

        if needed_col not in df.columns or consumed_col not in df.columns:
            print(f"Warning: Columns '{needed_col}' or '{consumed_col}' not found in DataFrame. Skipping plot for {nutrient}.")
            continue

        plt.figure(figsize=(8, 4)) # Slightly wider
        plt.plot(df["Day"], df[needed_col], label="Needed", marker='o', linestyle='--', color=color_needed, linewidth=2)
        plt.plot(df["Day"], df[consumed_col], label="Consumed", marker='s', linestyle='-', color=color_consumed, linewidth=2) # Changed marker

        plt.title(f"Weekly {nutrient} Intake vs Requirement", fontsize=14, pad=15) # Larger title
        plt.xlabel("Day of Week", fontsize=11)
        plt.ylabel(f"{nutrient} Amount", fontsize=11)
        plt.xticks(rotation=45, ha='right') # Rotate labels for better readability
        plt.legend(fontsize=10)
        plt.grid(True, linestyle=':', alpha=0.6) # Lighter grid
        plt.tight_layout() # Adjust layout to prevent labels overlapping

        filename = os.path.join(output_dir, f"{nutrient.lower()}_plot.png")
        try:
            plt.savefig(filename, dpi=200, bbox_inches='tight') # Slightly lower DPI for faster local generation
            plots[nutrient] = filename
            print(f"Generated plot: {filename}")
        except Exception as e:
            print(f"Error saving plot {filename}: {e}")
        finally:
             plt.close() # Ensure plot is closed


    # --- Generate Table Image ---
    # Select and rename columns for the table image for better readability
    table_df = df[[
        "Day",
        "Calories_Needed", "Calories_Consumed",
        "Protein_Needed", "Protein_Consumed",
        "Fats_Needed", "Fats_Consumed",
        "Fibre_Needed", "Fibre_Consumed"
    ]].copy()
    # Optional: Round values for cleaner display
    for col in table_df.columns:
        if "Needed" in col or "Consumed" in col:
            table_df[col] = table_df[col].round(1) # Round to 1 decimal place

    plt.figure(figsize=(12, 3)) # Adjust figure size based on number of columns
    plt.axis('off') # Hide axes

    # Create table - adjust styling as needed
    the_table = plt.table(
        cellText=table_df.values,
        colLabels=table_df.columns,
        cellLoc='center',
        loc='center',
        colColours=['#f8f9fa'] * len(table_df.columns) # Light grey header
    )

    the_table.auto_set_font_size(False)
    the_table.set_fontsize(9) # Adjust font size
    the_table.scale(1, 1.6) # Adjust cell height scale

    # Style header
    for (i, j), cell in the_table.get_celld().items():
        if i == 0: # Header row
            cell.set_text_props(weight='bold', color='black')
        cell.set_edgecolor('#d3d3d3') # Light grey cell borders
        cell.set_linewidth(0.5)


    table_filename = os.path.join(output_dir, "weekly_table.png")
    try:
        plt.savefig(table_filename, dpi=200, bbox_inches='tight', pad_inches=0.1)
        plots["table"] = table_filename
        print(f"Generated table image: {table_filename}")
    except Exception as e:
        print(f"Error saving table image {table_filename}: {e}")
    finally:
        plt.close() # Ensure plot is closed

    return plots

def generate_pdf_report(student_data, needs, weekly_summary_df, plots, output_dir=".", lang_code="en"):
    """Generate professional PDF report with visual enhancements (matching Colab style)"""
    pdf_filename = os.path.join(output_dir, f"Nutrition_Report_{student_data.get('name', 'UnknownStudent').replace(' ', '')}{datetime.now().strftime('%Y%m%d')}.pdf")

    try:
        pdf = FPDF()
        pdf.add_page()

        # Set green border for all pages
        pdf.set_draw_color(46, 204, 113)  # Green color
        pdf.rect(5, 5, 200, 287)  # Page border

        # Add larger logo (adjust path if needed, or comment out if no logo)
        logo_path = os.path.join(BASE_PATH, "logo.png") # Assuming logo.png in the same directory
        if os.path.exists(logo_path):
            pdf.image(logo_path, x=20, y=15, w=40)  # Increased size and position

        # Title
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(0, 30, "Nutrition Report", ln=1, align='C')  # Increased space

        # Student Info Section
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, "Student Information", ln=1)
        pdf.set_font("Arial", '', 12)
        info_lines = [
            f"Name: {student_data.get('name', 'N/A')}",
            f"Age: {student_data.get('age', 'N/A')} years",
            f"Gender: {student_data.get('gender', 'N/A').capitalize()}",
            f"Weight: {student_data.get('weight', 'N/A')} kg",
            f"Height: {student_data.get('height', 'N/A')} m",
            f"BMI: {needs.get('bmi', 'N/A')}"
        ]
        for line in info_lines:
            pdf.cell(0, 7, line, ln=1)  # Tighter line spacing
        pdf.ln(5)

        # Weekly Summary Table - better formatting
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, "Weekly Nutrition Summary", ln=1)

        # Scale table to fit page width
        if "table" in plots and os.path.exists(plots["table"]):
            table_width = 190
            table_height = 80  # Increased height for better readability
            pdf.image(plots["table"], x=(210-table_width)/2, w=table_width, h=table_height)
            pdf.ln(10)
        else:
            pdf.set_font("Arial", 'I', 10)
            pdf.cell(0, 7, "Weekly summary table not available.", ln=1)
            pdf.ln(5)

        # Nutrition Plots - 2x2 grid on one page
        pdf.add_page()
        pdf.set_draw_color(46, 204, 113)  # Green border for new page
        pdf.rect(5, 5, 200, 287)

        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 10, "Nutrition Analysis", ln=1, align='C')
        pdf.ln(5)

        # Calculate positions for 2x2 grid
        img_width = 90
        img_height = 60
        x_positions = [15, 105]
        y_positions = [50, 120]

        nutrients_to_plot = ["Calories", "Protein", "Fats", "Fibre"]
        for i, nutrient in enumerate(nutrients_to_plot):
            if nutrient in plots and os.path.exists(plots[nutrient]):
                x = x_positions[i % 2]
                y = y_positions[i // 2]
                pdf.set_xy(x, y-10)
                pdf.set_font("Arial", 'B', 10)
                pdf.cell(40, 5, f"{nutrient} Comparison", ln=0)
                pdf.image(plots[nutrient], x=x, y=y, w=img_width, h=img_height)
            else:
                x = x_positions[i % 2]
                y = y_positions[i // 2]
                pdf.set_xy(x, y)
                pdf.set_font("Arial", 'I', 10)
                pdf.cell(img_width, img_height, f"{nutrient} plot not available.", border=1, align='C')

        # Save PDF
        pdf.output(pdf_filename, "F")
        print(f"Successfully generated PDF: {pdf_filename}")
        return pdf_filename

    except Exception as e:
        print(f"Error generating PDF report: {e}")
        import traceback
        traceback.print_exc()
        if os.path.exists(pdf_filename):
            try:
                os.remove(pdf_filename)
            except OSError:
                 print(f"Could not remove incomplete PDF: {pdf_filename}")
        return None
    finally:
        # Clean up temporary plot files
        if os.path.exists(TEMP_PLOT_DIR):
            for nutrient, filename in plots.items():
                if os.path.exists(filename):
                    try:
                        os.remove(filename)
                    except OSError as err:
                        print(f"Error removing temporary file {filename}: {err}")
            try:
                if not os.listdir(TEMP_PLOT_DIR):
                    os.rmdir(TEMP_PLOT_DIR)
                else:
                    print(f"Warning: Temporary plot directory '{TEMP_PLOT_DIR}' not empty after cleanup.")
            except OSError as err:
                print(f"Error removing temporary plot directory '{TEMP_PLOT_DIR}': {err}")


# ----- Flask Routes -----

@app.route('/generate_nutrition_report_endpoint', methods=['GET'])
def generate_nutrition_report_endpoint():
    """Flask endpoint to trigger report generation and serve the PDF."""
    print(f"Received request to generate report for student ID: {student_id_to_process}")

    # 1. Fetch Student Data
    student_data = fetch_student_data(student_id_to_process)
    if not student_data:
        print(f"Error: Student data not found for ID {student_id_to_process}.")
        return jsonify({"error": f"Student not found: {student_id_to_process}"}), 404

    print(f"Student data fetched: {student_data.get('name', 'N/A')}")

    # 2. Calculate Nutritional Needs
    needs = calculate_daily_needs(
        student_data.get("weight"),
        student_data.get("height"),
        student_data.get("age"),
        student_data.get("gender")
    )
    if needs['calories'] == 0: # Check if calculation failed
        print("Error: Failed to calculate daily nutritional needs.")
        return jsonify({"error": "Failed to calculate nutritional needs. Check student data (weight, height, age)."}), 500

    print(f"Calculated daily needs: {needs}")

    # 3. Fetch Weekly Intake Data
    # raw_weekly_data = fetch_weekly_nutrition(student_id_to_process)
    raw_weekly_data = pd.DataFrame({
        "created_at": pd.to_datetime(['2025-04-07', '2025-04-08', '2025-04-09', '2025-04-10', '2025-04-11', '2025-04-12', '2025-04-13']),
        "calories": [2500, 2200, 2300, 2400, 2100, 2000, 1800],
        "protein": [80, 75, 85, 70, 65, 60, 55],
        "fats": [60, 55, 65, 50, 45, 40, 35],
        "fibre": [25, 20, 22, 18, 15, 12, 10],
        "student_id": [student_id_to_process] * 7
    })

    if raw_weekly_data.empty:
        # Decide if this is an error or just means no intake logged
        print(f"Warning: No food intake data found for student ID {student_id_to_process}. Report will show 0 consumption.")
        # Proceeding with zero consumption data might be desired. If not, return error:
        # return jsonify({"error": f"No nutrition intake data found for student: {student_id_to_process}"}), 404

    # 4. Aggregate Intake Data
    daily_consumption_summary = aggregate_daily_intake(raw_weekly_data)
    print("Aggregated daily consumption summary:")
    print(daily_consumption_summary)

    # 5. Prepare DataFrame for Plotting (Merge Needs and Consumption)
    # Create a base DataFrame with all days of the week
    all_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    plot_df = pd.DataFrame({'Day': all_days})

    # Add needed columns
    plot_df["Calories_Needed"] = needs["calories"]
    plot_df["Protein_Needed"] = needs["protein"]
    plot_df["Fats_Needed"] = needs["fats"]
    plot_df["Fibre_Needed"] = needs["fibre"]

    # Merge with consumption data (use left merge to keep all days)
    plot_df = pd.merge(plot_df, daily_consumption_summary, on="Day", how="left")
    # Fill NaN values with 0 for days with no consumption data
    plot_df = plot_df.fillna(0)

    print("Final DataFrame for plotting:")
    print(plot_df)

    # 6. Generate Plots
    # Create a temporary directory for plots specific to this request might be safer
    # if handling concurrent requests, but for simple local use, TEMP_PLOT_DIR is ok.
    plots = generate_plots(plot_df, TEMP_PLOT_DIR)
    if not plots or not any(plots.values()):
         print("Error: Failed to generate plots.")
         # Cleanup potentially created plot dir even if plots failed
         if os.path.exists(TEMP_PLOT_DIR):
             try:
                 if not os.listdir(TEMP_PLOT_DIR): os.rmdir(TEMP_PLOT_DIR)
             except OSError: pass
         return jsonify({"error": "Failed to generate analysis plots"}), 500

    # 7. Generate PDF Report
    pdf_filepath = generate_pdf_report(student_data, needs, plot_df, plots, output_dir=BASE_PATH) # Save PDF in base path

    # Note: Cleanup of temp plot files happens inside generate_pdf_report

    # 8. Serve the PDF
    if pdf_filepath and os.path.exists(pdf_filepath):
        print(f"Sending PDF file: {pdf_filepath}")
        try:
            return send_file(
                pdf_filepath,
                as_attachment=True, # Makes the browser prompt for download
                download_name=os.path.basename(pdf_filepath) # Sets the suggested filename
                # mimetype='application/pdf' # Usually inferred correctly
             )
        except Exception as e:
            print(f"Error sending file: {e}")
            return jsonify({"error": "Could not send PDF file"}), 500
    else:
        print("Error: PDF file path not generated or file does not exist.")
        return jsonify({"error": "Failed to generate or find PDF report file"}), 500

# ----- Main Execution -----
if _name_ == '_main_':
    # Check for Supabase credentials before starting
    if not SUPABASE_URL or "YOUR_SUPABASE_URL" in SUPABASE_URL or \
       not SUPABASE_KEY or "YOUR_SUPABASE_ANON_KEY" in SUPABASE_KEY:
        print("-" * 50)
        print("ERROR: Supabase URL or Key not set.")
        print("Please replace 'YOUR_SUPABASE_URL' and 'YOUR_SUPABASE_ANON_KEY' in the script.")
        print("-" * 50)
    elif not supabase:
         print("-" * 50)
         print("ERROR: Supabase client failed to initialize. Cannot start server.")
         print("Check connection or credentials.")
         print("-" * 50)
    else:
        print("Starting Flask server...")
        # debug=True automatically reloads the server when code changes,
        # but should be False in a production environment.
        # host='0.0.0.0' makes the server accessible on your network,
        # use '127.0.0.1' (default) for local access only.