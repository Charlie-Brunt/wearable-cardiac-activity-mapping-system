import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import norm

# Step 1: Generate a dataset
np.random.seed(0)  # For reproducibility
data = 5*np.random.normal(loc=0, scale=1, size=1000)

# Step 2: Create a histogram of the data
fig, ax = plt.subplots(figsize=(8, 6))
ax.hist(data, bins=30, density=True, alpha=0.6, color='g', label='Histogram')

# Step 3: Fit a Gaussian to the histogram data
mean, std = norm.fit(data)

# Step 4: Get the current x-axis limits
xmin, xmax = ax.get_xlim()

# Generate x values for plotting the Gaussian curve within the x-axis limits
x = np.linspace(xmin, xmax, 100)

# Calculate the Gaussian probability density function (pdf) values
p = norm.pdf(x, mean, std)

# Plot the Gaussian curve
ax.plot(x, p, 'k', linewidth=2, label='Fitted Gaussian')

# Add titles and labels
ax.set_title('Histogram and Fitted Gaussian')
ax.set_xlabel('Value')
ax.set_ylabel('Frequency')
ax.legend()

# Show the plot
plt.show()