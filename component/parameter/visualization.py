from component.parameter.module_parameter import LC_CLASSES
import pandas as pd

df = pd.read_csv(LC_CLASSES, header=0)


degradation = {
    "palette": ["#8B0000", "#B0C4DE", "#008000"],
    "max": 3,
    "min": 1,
}

degrad_label = {
    "degraded": "Degraded",
    "stable": "Stable",
    "improved": "Improved",
}

degradation_legend = {
    label: color for label, color in zip(degrad_label.values(), degradation["palette"])
}

land_cover = {"max": len(df), "min": 1, "palette": list(df.color.tolist())}
land_cover_legend = {
    label: color for label, color in zip(df.desc.tolist(), df.color.tolist())
}


VIS_PARAMS = {
    "land_cover": land_cover,
    "degradation": degradation,
}

LEGENDS = {
    "land_cover": land_cover_legend,
    "degradation": degradation_legend,
}
