from pathlib import Path
from typing import List as ListType, Dict as DictType, Any
import ipyvuetify as v
from traitlets import Dict, List, Unicode, observe
import logging
import sepal_ui.sepalwidgets as sw
import component.parameter.module_parameter as param

log = logging.getLogger("MGCI.widget.custom_list")


class CustomListA(v.VuetifyTemplate, sw.SepalWidget):
    """Custom list component for sub-indicator A calculations.

    Manages reporting years with asset and year selection pairs.
    Uses Vue.js for efficient UI rendering and updates.
    """

    # Point to Vue template
    template_file = Unicode(str(Path(__file__).parent / "vue/customListA.vue")).tag(
        sync=True
    )

    # Synchronized properties with Vue
    v_model = Dict({}, allow_none=True).tag(sync=True)
    items = List([]).tag(sync=True)
    years = List([]).tag(sync=True)
    errors = List([]).tag(sync=True)
    max_items = Unicode("9").tag(sync=True)  # Max 10 items (0-9 indices)

    # Labels for localization
    title = Unicode("Reporting years").tag(sync=True)
    asset_label = Unicode("").tag(sync=True)
    year_label = Unicode("").tag(sync=True)

    def __init__(self, items: ListType = None, **kwargs):
        """Initialize CustomListA component.

        Args:
            items: List of available items for selection
        """
        super().__init__(**kwargs)

        # Set initial data with some default items for testing
        self.items = items or [
            "users/your-username/asset1",
            "users/your-username/asset2",
            "users/your-username/asset3",
        ]
        self.asset_label = "Year"
        self.year_label = "Corresponding year"
        self.years = param.YEARS

        # Initialize with one empty item (like legacy)
        self.v_model = {1: {"asset": None, "year": None}}

        log.debug(f"CustomListA initialized with {len(self.items)} items")

    @observe("v_model")
    def _on_model_changed(self, change):
        """Handle v_model changes to trigger Vue reactivity and validation."""
        log.debug(f"CustomListA v_model changed: {change['new']}")

        # Trigger Vue reactivity for manual assignments
        if change["type"] == "change" and hasattr(self, "send"):
            self.send({"method": "set_model", "args": [change["new"]]})

        # Validate the new model
        self._validate_model()

    def _validate_model(self):
        """Validate current model and update errors."""
        errors = []

        for key, value in self.v_model.items():
            if isinstance(value, dict):
                if not value.get("asset"):
                    errors.append(f"Asset required for item {key}")
                if not value.get("year"):
                    errors.append(f"Year required for item {key}")

        self.errors = errors

    def populate(self, new_items):
        """Update items from Vue component.

        Args:
            new_items: New list of items to populate
        """
        self.items = list(new_items)  # Create new list to trigger sync
        log.debug(f"Items populated: {len(self.items)} items")

    def validate(self):
        """Validate current data from Vue component."""
        self._validate_model()
        return len(self.errors) == 0

    def set_default(self):
        """Set default values for the component."""
        try:
            # Ensure we have items to select from
            if not self.items:
                log.warning("No items available for default selection")
                return

            # Extract actual item values from the dictionary structure
            item_values = []
            for item in self.items:
                if isinstance(item, dict) and "value" in item:
                    item_values.append(item["value"])
                elif isinstance(item, str):
                    item_values.append(item)

            # Check if LULC_DEFAULT assets are available in items
            lulc_items = [
                item for item in item_values if item.startswith(param.LULC_DEFAULT)
            ]

            if lulc_items:
                # Use the predefined default if LULC_DEFAULT assets are available
                default_asset = param.DEFAULT_ASSETS["sub_a"][1]["asset_id"]
                default_year = param.DEFAULT_ASSETS["sub_a"][1]["year"]

                # Check if the specific default asset is in items
                if default_asset not in item_values:
                    # Try to find a close match based on year
                    year_suffix = f"/{default_year}"
                    matching_item = next(
                        (item for item in lulc_items if item.endswith(year_suffix)),
                        None,
                    )
                    if matching_item:
                        default_asset = matching_item
                    else:
                        # Fall back to first available LULC item
                        default_asset = lulc_items[0]
                        # Extract year from asset path
                        try:
                            default_year = int(default_asset.split("/")[-1])
                        except (ValueError, IndexError):
                            default_year = param.DEFAULT_ASSETS["sub_a"][1]["year"]
                        log.info(f"Using fallback LULC asset: {default_asset}")
            else:
                # No LULC_DEFAULT assets available - reset to clean state
                log.info(
                    "No LULC_DEFAULT assets found in items, resetting CustomListA to clean state"
                )
                self.reset()
                return

            # Create completely new v_model object to trigger sync
            new_model = {1: {"asset": default_asset, "year": default_year}}

            # Now simply assign to v_model property - it handles reactivity automatically
            self.v_model = new_model

            # Force validation update
            self._validate_model()

            log.debug(
                f"CustomListA default values set: asset={default_asset}, year={default_year}"
            )
            log.debug(f"New v_model: {self.v_model}")
        except Exception as e:
            log.error(f"Could not set default values: {e}")
            raise ValueError(f"Could not set default values: {e}")

    def reset(self):
        """Reset the component to empty state."""
        self.v_model = {1: {"asset": None, "year": None}}
        self.errors = []
        log.debug("CustomListA reset completed")


class CustomListB(v.VuetifyTemplate, sw.SepalWidget):
    """Custom list component for sub-indicator B calculations.

    Manages baseline period and reporting years with asset and year selection pairs.
    Uses Vue.js for efficient UI rendering and updates.
    """

    # Point to Vue template
    template_file = Unicode(str(Path(__file__).parent / "vue/customListB.vue")).tag(
        sync=True
    )

    # Synchronized properties with Vue
    v_model = Dict({}, allow_none=True).tag(sync=True)
    items = List([]).tag(sync=True)
    years = List([]).tag(sync=True)
    errors = List([]).tag(sync=True)
    max_items = Unicode("9").tag(sync=True)  # Max 10 items (0-9 indices)

    # Labels for localization
    baseline_title = Unicode("").tag(sync=True)
    reporting_title = Unicode("").tag(sync=True)
    reporting_subtitle = Unicode("").tag(sync=True)
    start_year_label = Unicode("").tag(sync=True)
    end_year_label = Unicode("").tag(sync=True)
    asset_label = Unicode("").tag(sync=True)
    year_label = Unicode("").tag(sync=True)

    def __init__(self, items: ListType = None, **kwargs):
        """Initialize CustomListB component.

        Args:
            items: List of available items for selection
        """
        super().__init__(**kwargs)

        # Set initial data
        self.items = items or []

        # Set labels
        self.baseline_title = "Baseline period"
        self.reporting_title = "Reporting years"
        self.reporting_subtitle = "Each year will be reported against the baseline"
        self.start_year_label = "Initial year"
        self.end_year_label = "Final year"
        self.asset_label = "Year"
        self.year_label = "Corresponding year"
        self.years = param.YEARS

        self.items = items or [
            "users/your-username/asset1",
            "users/your-username/asset2",
            "users/your-username/asset3",
        ]

        # Initialize with baseline structure and one reporting year (like legacy implementation)
        self.v_model = {
            "baseline": {
                "base": {"asset": None, "year": None},
                "report": {"asset": None, "year": None},
            },
            2: {"asset": None, "year": None},
        }

        log.debug(f"CustomListB initialized with {len(self.items)} items")

    @observe("v_model")
    def _on_model_changed(self, change):
        """Handle v_model changes to trigger Vue reactivity and validation."""
        log.debug(f"CustomListB v_model changed: {change['new']}")

        # Trigger Vue reactivity for manual assignments
        if change["type"] == "change" and hasattr(self, "send"):
            self.send({"method": "set_model", "args": [change["new"]]})

        # Validate the new model
        self._validate_model()

    def _validate_model(self):
        """Validate current model and update errors."""
        errors = []

        # Validate baseline
        baseline = self.v_model.get("baseline", {})
        if isinstance(baseline, dict):
            for period in ["base", "report"]:
                period_data = baseline.get(period, {})
                if isinstance(period_data, dict):
                    if not period_data.get("asset"):
                        errors.append(f"Asset required for baseline {period}")
                    if not period_data.get("year"):
                        errors.append(f"Year required for baseline {period}")

        # Validate reporting years
        for key, value in self.v_model.items():
            if key != "baseline" and isinstance(value, dict):
                if not value.get("asset"):
                    errors.append(f"Asset required for reporting year {key}")
                if not value.get("year"):
                    errors.append(f"Year required for reporting year {key}")

        # Validate baseline year order
        try:
            baseline = self.v_model.get("baseline", {})
            base_year = baseline.get("base", {}).get("year")
            report_year = baseline.get("report", {}).get("year")

            if base_year and report_year and base_year >= report_year:
                errors.append("Start year must be before end year in baseline period")
        except (TypeError, ValueError):
            pass

        self.errors = errors

    def populate(self, new_items):
        """Update items from Vue component.

        Args:
            new_items: New list of items to populate
        """
        self.items = list(new_items)  # Create new list to trigger sync
        log.debug(f"Items populated: {len(self.items)} items")

    def validate(self):
        """Validate current data from Vue component."""
        self._validate_model()
        return len(self.errors) == 0

    def reset(self):
        """Reset the component to empty state."""
        self.v_model = {
            "baseline": {
                "base": {"asset": None, "year": None},
                "report": {"asset": None, "year": None},
            },
            2: {"asset": None, "year": None},
        }
        self.errors = []
        log.debug("CustomListB reset completed")

    def set_default(self):
        """Set default values for the component."""
        try:
            # Ensure we have items to select from
            if not self.items:
                log.warning("No items available for default selection")
                return

            # Extract actual item values from the dictionary structure
            item_values = []
            for item in self.items:
                if isinstance(item, dict) and "value" in item:
                    item_values.append(item["value"])
                elif isinstance(item, str):
                    item_values.append(item)

            # Check if LULC_DEFAULT assets are available in items
            lulc_items = [
                item for item in item_values if item.startswith(param.LULC_DEFAULT)
            ]

            if lulc_items:
                # Use the predefined defaults if LULC_DEFAULT assets are available
                baseline = param.DEFAULT_ASSETS["sub_b"]["baseline"]
                report = param.DEFAULT_ASSETS["sub_b"]["report"]

                base_start_asset = baseline["start_year"]["asset_id"]
                base_start_year = baseline["start_year"]["year"]

                base_end_asset = baseline["end_year"]["asset_id"]
                base_end_year = baseline["end_year"]["year"]

                report_asset = report["asset_id"]
                report_year = report["year"]

                # Check if the specific default assets are in items, otherwise find alternatives
                if base_start_asset not in item_values:
                    year_suffix = f"/{base_start_year}"
                    matching_item = next(
                        (item for item in lulc_items if item.endswith(year_suffix)),
                        None,
                    )
                    base_start_asset = matching_item or lulc_items[0]
                    if not matching_item:
                        try:
                            base_start_year = int(base_start_asset.split("/")[-1])
                        except (ValueError, IndexError):
                            pass

                if base_end_asset not in item_values:
                    year_suffix = f"/{base_end_year}"
                    matching_item = next(
                        (item for item in lulc_items if item.endswith(year_suffix)),
                        None,
                    )
                    base_end_asset = (
                        matching_item or lulc_items[-1]
                    )  # Use last item for end year
                    if not matching_item:
                        try:
                            base_end_year = int(base_end_asset.split("/")[-1])
                        except (ValueError, IndexError):
                            pass

                if report_asset not in item_values:
                    year_suffix = f"/{report_year}"
                    matching_item = next(
                        (item for item in lulc_items if item.endswith(year_suffix)),
                        None,
                    )
                    report_asset = (
                        matching_item or lulc_items[-1]
                    )  # Use last available item
                    if not matching_item:
                        try:
                            report_year = int(report_asset.split("/")[-1])
                        except (ValueError, IndexError):
                            pass

                # Create completely new v_model object to trigger sync
                new_model = {
                    "baseline": {
                        "base": {"asset": base_start_asset, "year": base_start_year},
                        "report": {"asset": base_end_asset, "year": base_end_year},
                    },
                    2: {"asset": report_asset, "year": report_year},
                }

                # Now simply assign to v_model property - it handles reactivity automatically
                self.v_model = new_model

                # Force validation update
                self._validate_model()

                log.debug(
                    f"CustomListB default values set: baseline=({base_start_asset}, {base_start_year})-({base_end_asset}, {base_end_year}), report=({report_asset}, {report_year})"
                )
                log.debug(f"New v_model: {self.v_model}")
            else:
                # No LULC_DEFAULT assets available - reset to clean state
                log.info(
                    "No LULC_DEFAULT assets found in items, resetting CustomListB to clean state"
                )
                self.reset()
                return

        except Exception as e:
            log.warning(f"Could not set default values: {e}")
