# Task: Build a New "Country" Page with Dynamic Dropdowns and a Treemap Visualization

Create a new page titled **"Country"** in addition to the existing **About** and **Table** pages. This new page should include the following functionality:

### Data to use
Use the same data as the bubble chat from callbacks.py


## 1. Dropdown Menus:
- **First Dropdown:** Allows users to select a **sector** from a list of available sectors.
- **Second Dropdown:** Displays a list of **securities** corresponding to the selected sector. Users can choose a specific security from this list.

## 2. Treemap Visualization:
- Once a security is selected, a **Treemap chart** should be displayed showing the **country-level exposure** for that security. 
- The size of each country should represent the **percentage of the security's exposure** to that country. 
- The Treemap should allow users to hover over each country to see details about the exposure percentage.

## Example Treemap Plot using Plotly:
The Treemap chart should resemble the one below, which displays country-level exposure data for a security:

```python
import plotly.express as px
import numpy as np

df = px.data.gapminder().query("year == 2007")

fig = px.treemap(df, path=[px.Constant("world"), 'continent', 'country'], values='pop',
                  color='lifeExp', hover_data=['iso_alpha'],
                  color_continuous_scale='RdBu',
                  color_continuous_midpoint=np.average(df['lifeExp'], weights=df['pop']))

fig.update_layout(margin = dict(t=50, l=25, r=25, b=25))
fig.show()
