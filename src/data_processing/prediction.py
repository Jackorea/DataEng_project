import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing
import warnings

warnings.filterwarnings("ignore")

def forecast_movie_releases(release_years_data):
    if not release_years_data.empty:
        model = ExponentialSmoothing(release_years_data["count"], trend="add", seasonal=None)
        fit = model.fit()
        future_years = list(range(release_years_data["year"].max() + 1, release_years_data["year"].max() + 6))
        predictions = fit.forecast(len(future_years))
        return pd.DataFrame({"year": future_years, "count": predictions})
    return release_years_data
