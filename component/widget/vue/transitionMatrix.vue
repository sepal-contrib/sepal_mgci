<template>
  <div>
    <!-- Toolbar -->
    <v-toolbar flat id="transition_matrix" class="mb-2">
      <v-toolbar-title>Transition matrix</v-toolbar-title>
      <v-spacer></v-spacer>
      <v-divider vertical class="mx-2"></v-divider>
      <v-btn icon @click="setDefaultValues">
        <v-icon>mdi-broom</v-icon>
      </v-btn>
    </v-toolbar>

    <!-- Progress bar -->
    <v-progress-linear
      v-if="loading"
      :indeterminate="loading"
      height="5"
      id="transition_matrix"
      class="mb-2"
    />

    <!-- Transition Matrix Table -->
    <v-simple-table id="transition_matrix" v-if="matrixData.length > 0">
      <template v-slot:default>
        <tbody>
          <!-- Header row -->
          <tr>
            <th></th>
            <th
              v-for="(classItem, index) in classes"
              :key="`header-${index}`"
              class="text-center"
            >
              <v-tooltip
                v-if="classItem.length > 20"
                bottom
                max-width="175"
              >
                <template v-slot:activator="{ on, attrs }">
                  <span v-bind="attrs" v-on="on">
                    {{ truncateString(classItem) }}
                  </span>
                </template>
                <span>{{ classItem }}</span>
              </v-tooltip>
              <span v-else>{{ classItem }}</span>
            </th>
          </tr>

          <!-- Matrix rows -->
          <tr v-for="(row, rowIndex) in matrixData" :key="`row-${rowIndex}`">
            <!-- Row header -->
            <th class="text-center">
              <v-tooltip
                v-if="classes[rowIndex].length > 20"
                bottom
                max-width="175"
              >
                <template v-slot:activator="{ on, attrs }">
                  <span v-bind="attrs" v-on="on">
                    {{ truncateString(classes[rowIndex]) }}
                  </span>
                </template>
                <span>{{ classes[rowIndex] }}</span>
              </v-tooltip>
              <span v-else>{{ classes[rowIndex] }}</span>
            </th>

            <!-- Matrix cells -->
            <td
              v-for="(cell, colIndex) in row"
              :key="`cell-${rowIndex}-${colIndex}`"
              class="ma-0 pa-0"
              :style="{ backgroundColor: getCellColor(cell.value) }"
            >
              <v-select
                v-model="cell.value"
                :items="selectItems"
                :disabled="disabled"
                dense
                color="white"
                class="ma-1"
                @change="onCellChange(rowIndex + 1, colIndex + 1, cell.value)"
              />
            </td>
          </tr>
        </tbody>
      </template>
    </v-simple-table>

    <!-- Loading state -->
    <div v-else-if="loading" class="text-center pa-4">
      <v-progress-circular indeterminate></v-progress-circular>
      <div class="mt-2">Loading transition matrix...</div>
    </div>

    <!-- Empty state -->
    <div v-else class="text-center pa-4">
      <v-icon large color="grey">mdi-table</v-icon>
      <div class="mt-2 grey--text">No transition matrix data available</div>
    </div>
  </div>
</template>

<script>
modules.export = {
  name: "TransitionMatrix",

  props: {
    classes: {
      type: Array,
      default: () => [],
    },
    matrix_data: {
      type: Array,
      default: () => [],
    },
    decode_options: {
      type: Object,
      default: () => ({}),
    },
    disabled: {
      type: Boolean,
      default: false,
    },
    loading: {
      type: Boolean,
      default: false,
    },
  },

  data() {
    return {
      matrixData: [],
    };
  },

  mounted() {
    // Manually trigger matrix initialization since watchers might not fire on mount
    this.initializeMatrix(this.matrix_data);
  },

  computed: {
    selectItems() {
      return Object.values(this.decode_options).map((option) => ({
        text: option.abrv,
        value: option.abrv,
      }));
    },
  },

  watch: {
    matrix_data(newData) {
      // Ensure we have a valid array
      if (!Array.isArray(newData)) {
        newData = [];
      }
      this.initializeMatrix(newData);
    },
    classes(newClasses) {
      // Re-initialize matrix when classes change
      if (newClasses && newClasses.length > 0) {
        this.initializeMatrix(this.matrix_data);
      }
    },
  },

  methods: {
    initializeMatrix(data) {
      if (!data || data.length === 0) {
        this.matrixData = [];
        return;
      }

      if (!this.classes || this.classes.length === 0) {
        this.matrixData = [];
        return;
      }

      // Initialize matrix structure
      this.matrixData = this.classes.map((_, rowIndex) =>
        this.classes.map((_, colIndex) => {
          const dataPoint = data.find(
            (item) =>
              item.from_code === rowIndex + 1 && item.to_code === colIndex + 1
          );

          const impactCode = dataPoint ? dataPoint.impact_code : null;
          const defaultValue = impactCode
            ? this.getAbbreviationFromImpactCode(impactCode)
            : "";

          return {
            value: defaultValue,
            row: rowIndex + 1,
            col: colIndex + 1,
          };
        })
      );
    },

    getAbbreviationFromImpactCode(impactCode) {
      // Try multiple approaches to find the option
      let option = this.decode_options[impactCode] || 
                   this.decode_options[String(impactCode)] || 
                   this.decode_options[Number(impactCode)];
      
      // If still not found, try searching through all options
      if (!option) {
        for (const [key, value] of Object.entries(this.decode_options)) {
          if (key == impactCode || Number(key) === Number(impactCode)) {
            option = value;
            break;
          }
        }
      }
      
      return option ? option.abrv : "";
    },

    getImpactCodeFromAbbreviation(abbreviation) {
      const entry = Object.entries(this.decode_options).find(
        ([_, option]) => option.abrv === abbreviation
      );
      // Return the key as it is (could be string or number)
      return entry ? entry[0] : null;
    },

    getCellColor(value) {
      const impactCode = this.getImpactCodeFromAbbreviation(value);
      if (impactCode) {
        // Try multiple approaches to find the color
        let option = this.decode_options[impactCode] || 
                     this.decode_options[String(impactCode)] || 
                     this.decode_options[Number(impactCode)];
        
        if (option && option.color) {
          return option.color;
        }
      }
      return "#1976d2"; // Default primary color
    },

    onCellChange(row, col, value) {
      const impactCode = this.getImpactCodeFromAbbreviation(value);
      
      if (typeof this.cell_changed === 'function') {
        this.cell_changed({
          row: row,
          col: col,
          value: impactCode,
          abbreviation: value,
        });
      }
    },

    setDefaultValues() {
      if (typeof this.reset_to_default === 'function') {
        this.reset_to_default();
      }
    },

    truncateString(string) {
      if (string.length <= 20) return string;
      return string.slice(0, 7) + "..." + string.slice(-7);
    },
  },
};
</script>

<style scoped>
.v-data-table td {
  padding: 0 !important;
  margin: 0 !important;
}

.v-select {
  margin: 4px !important;
}

.v-input__control {
  min-height: unset !important;
}

/* Center text in dropdown */
.v-select .v-select__selection {
  text-align: center !important;
  justify-content: center !important;
}

/* Center text in dropdown menu items */
.v-select .v-list-item__title {
  text-align: center !important;
}

</style>
