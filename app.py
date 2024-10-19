from flask import Flask, request, render_template
import pickle
import plotly.graph_objects as go
import plotly.utils  
import json

app = Flask(__name__)

# Load the model
with open('recommendations_model.pkl', 'rb') as file:
    recommendations_data = pickle.load(file)

# Function to generate recommendations
def generate_recommendations(activities_above_threshold, user_emissions):
    generated_recommendations = []
    total_expected_reduction = 0

    for activity in activities_above_threshold:
        if activity in recommendations_data:
            rec = {
                'Activity': activity,
                'Current Emission': user_emissions[activity],
                'Recommendation': recommendations_data[activity]['Recommendation'],
                'Expected Reduction (kg CO2)': recommendations_data[activity]['Reduction']  # Ensure this is correct
            }
            generated_recommendations.append(rec)
            total_expected_reduction += recommendations_data[activity]['Reduction']
    
    return generated_recommendations, total_expected_reduction


@app.route('/')
def index():
    return render_template('climate_navigator.html')

@app.route('/recommend', methods=['POST'])
def recommend():
    # Get user input from form
    daily_commute_distance = float(request.form['daily_commute_distance'])
    transportation_mode = request.form['transportation_mode']
    ac_usage_hours = float(request.form['ac_usage_hours'])
    led_lighting_hours = float(request.form['led_lighting_hours'])
    washing_machine_usage = int(request.form['washing_machine_usage'])
    organic_waste_generated = float(request.form['organic_waste_generated'])
    plastic_waste_generated = float(request.form['plastic_waste_generated'])

    # New user emissions based on updated formula
    emission_factors = {
        'Car(Petrol)': 0.12,
    'Car(Diesel)': 0.15,
    'Bike(Petrol)': 0.05,
    'Public Bus': 0.03,
    'Metro(Electric)': 0.02,  # You might want to adjust this value based on your research
    'Walking': 0.0,
    'Air Conditioner (AC)': 1.2,
    'LED Lighting': 0.01,
    'Washing Machine': 0.5,
    'Organic Waste': 0.1,
    'Plastic Waste': 0.2
    }

    user_emissions = {
        'Transportation': daily_commute_distance * emission_factors[transportation_mode],
        'AC Usage': ac_usage_hours * emission_factors['Air Conditioner (AC)'],
        'Lighting': led_lighting_hours * emission_factors['LED Lighting'],
        'Washing Machine': (washing_machine_usage / 7) * emission_factors['Washing Machine'],
        'Organic Waste': organic_waste_generated * emission_factors['Organic Waste'],
        'Plastic Waste': plastic_waste_generated * emission_factors['Plastic Waste']
    }

    # Acceptable values for emissions
    acceptable_values = {
        'Transportation': 5.0,
        'AC Usage': 3.0,
        'Lighting': 1.0,
        'Washing Machine': 2.0,
        'Organic Waste': 1.0,
        'Plastic Waste': 1.5
    }

    # Activities above acceptable levels
    activities_above_threshold = [activity for activity, emission in user_emissions.items() if emission > acceptable_values[activity]]

    # Generate recommendations
    generated_recommendations, total_expected_reduction = generate_recommendations(activities_above_threshold, user_emissions)

    # Calculate goal emissions
    total_footprint = sum(user_emissions.values())
    goal_emission = total_footprint - total_expected_reduction

    # Prepare data for Plotly graphs
    activities = list(user_emissions.keys())
    current_emissions = list(user_emissions.values())
    recommended_emissions = [user_emissions[activity] - next((rec['Expected Reduction (kg CO2)'] for rec in generated_recommendations if rec['Activity'] == activity), 0) for activity in activities]

    # Create the bar chart
    bar_fig = go.Figure(data=[
        go.Bar(name='Current Emissions (kg CO2)', x=activities, y=current_emissions),
        go.Bar(name='Recommended Emissions (kg CO2)', x=activities, y=recommended_emissions)
    ])
    bar_fig.update_layout(title='Comparison of Current and Recommended Carbon Emissions',
                          xaxis_title='Activities',
                          yaxis_title='Emissions (kg CO2)',
                          barmode='group')

    # Create the line chart for current vs goal emissions
    line_fig = go.Figure()
    line_fig.add_trace(go.Scatter(x=['Current Emissions', 'Goal Emissions'], 
                                   y=[total_footprint, goal_emission],
                                   mode='lines+markers', name='Emissions',
                                   line=dict(color='blue', width=2)))
    line_fig.update_layout(title='Current vs Goal Carbon Emissions',
                           xaxis_title='Emission Category',
                           yaxis_title='Emissions (kg CO2)')

    # Convert figures to JSON for rendering in the template
    bar_fig_json = json.dumps(bar_fig, cls=plotly.utils.PlotlyJSONEncoder)
    line_fig_json = json.dumps(line_fig, cls=plotly.utils.PlotlyJSONEncoder)

    return render_template('recommendations.html', recommendations=generated_recommendations,
                           total_reduction=total_expected_reduction, total_footprint=total_footprint,
                           goal_emission=goal_emission, bar_fig_json=bar_fig_json, line_fig_json=line_fig_json)

if __name__ == '__main__':
    app.run(debug=True)
