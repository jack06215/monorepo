import dagster
import pandas as pd

from python.termux_backend.dagster import workspace_definition


@dagster.asset
def processed_data() -> None:
    # Read data from the CSV
    df = pd.read_csv(workspace_definition.PROJECT_ROOT / "data" / "sample_data.csv")
    # Add an age_group column based on the value of age
    df["age_group"] = pd.cut(
        df["age"],
        bins=[0, 30, 40, 100],
        labels=["Young", "Middle", "Senior"],
    )

    # Save processed data
    df.to_csv(
        workspace_definition.PROJECT_ROOT / "data" / "processed_data.csv",
        index=False,
    )


# Tell Dagster about the assets that make up the pipeline by
# passing it to the Definitions object
# This allows Dagster to manage the assets' execution and dependencies
defs = dagster.Definitions(assets=[processed_data])
