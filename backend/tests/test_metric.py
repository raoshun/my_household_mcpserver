def test_metric_model():
    from household_mcp.models.metric import Metric

    met = Metric(
        name="前年同月比",
        description="前年同月との比較",
        formula="(今年-去年)/去年*100",
    )
    assert met.name == "前年同月比"
