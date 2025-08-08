<template>
  <v-card class="ma-2">
    <!-- Toolbar with reset button -->
    
    <!-- Baseline Section -->
    <v-card class="mb-4">
      <v-card-title>
        {{ baseline_title }}
      </v-card-title>
      
      <v-card-text>
        <!-- Start Year (Base) -->
        <v-row align="center" class="mb-3">
          <v-col cols="1" class="text-center">
            <span class="text-h6">2000</span>
          </v-col>
          <v-col cols="9">
            <v-select
              :value="baselineBase.asset"
              @input="updateBaseline('base', 'asset', $event)"
              :items="sortedItemsAsc"
              :label="start_year_label"
              dense
              placeholder="GEE Asset ID"
              :error="hasBaselineError('base', 'asset')"
              :error-messages="getBaselineError('base', 'asset')"
            />
          </v-col>
          <v-col cols="2">
            <v-select
              :value="baselineBase.year"
              @input="updateBaseline('base', 'year', $event)"
              :items="yearItems"
              :label="year_label"
              dense
              type="number"
              :error="hasBaselineError('base', 'year')"
              :error-messages="getBaselineError('base', 'year')"
            />
          </v-col>
        </v-row>
        
        <!-- End Year (Report) -->
        <v-row align="center">
          <v-col cols="1" class="text-center">
            <span class="text-h6">2015</span>
          </v-col>
          <v-col cols="9">
            <v-select
              :value="baselineReport.asset"
              @input="updateBaseline('report', 'asset', $event)"
              :items="sortedItemsDesc"
              :label="end_year_label"
              dense
              placeholder="GEE Asset ID"
              :error="hasBaselineError('report', 'asset')"
              :error-messages="getBaselineError('report', 'asset')"
            />
          </v-col>
          <v-col cols="2">
            <v-select
              :value="baselineReport.year"
              @input="updateBaseline('report', 'year', $event)"
              :items="yearItemsDesc"
              :label="year_label"
              dense
              type="number"
              :error="hasBaselineError('report', 'year')"
              :error-messages="getBaselineError('report', 'year')"
            />
          </v-col>
        </v-row>
      </v-card-text>
      
      <v-card-actions>
        <v-spacer />
        <v-btn
          v-if="reportingItems.length === 0"
          icon
          @click="addReportingItem"
          :disabled="reportingItems.length >= parseInt(max_items)"
        >
          <v-icon>mdi-plus</v-icon>
        </v-btn>
      </v-card-actions>
    </v-card>
    
    <!-- Reporting Years Section -->
    <div v-if="reportingItems.length > 0">
      <div class="d-flex align-center mb-3">
        <v-card-title>{{ reporting_title }}</v-card-title>
      </div>
      <v-card-subtitle>{{ reporting_subtitle }}</v-card-subtitle>
      
      <div v-for="(item, index) in reportingItems" :key="item.id" class="mb-4">
        <v-row align="center">
          <!-- Asset Selection - Uses most space -->
          <v-col cols="9">
            <v-select
              :value="item.asset"
              @input="updateReportingItem(item.id, 'asset', $event)"
              :items="items"
              :label="asset_label"
              dense
              placeholder="GEE Asset ID"
              :error="hasReportingError(item.id, 'asset')"
              :error-messages="getReportingError(item.id, 'asset')"
            />
          </v-col>
          
          <!-- Year Selection - Fixed width -->
          <v-col cols="2">
            <v-select
              :value="item.year"
              @input="updateReportingItem(item.id, 'year', $event)"
              :items="yearItems"
              :label="year_label"
              dense
              type="number"
              :error="hasReportingError(item.id, 'year')"
              :error-messages="getReportingError(item.id, 'year')"
            />
          </v-col>
          
          <!-- Actions -->
          <v-col cols="1" class="d-flex justify-center">
            <!-- Add button always appears on first reporting item -->
            <v-btn
              v-if="index === 0"
              icon
              @click="addReportingItem"
              :disabled="reportingItems.length >= parseInt(max_items)"
            >
              <v-icon>mdi-plus</v-icon>
            </v-btn>
            
            <!-- Remove button appears on all reporting items except the first -->
            <v-btn
              v-if="index > 0"
              icon
              @click="removeReportingItem(item.id)"
            >
              <v-icon>mdi-minus</v-icon>
            </v-btn>
          </v-col>
        </v-row>
        
        <v-divider v-if="index < reportingItems.length - 1" class="my-2" />
      </div>
      
      <!-- Remove the additional add button section since + is always on first reporting item -->
    </div>
  </v-card>
</template>

<script>
export default {
  name: 'CustomListB',
  
  props: {
    v_model: { type: Object, default: () => ({}) },
    items: { type: Array, default: () => [] },
    years: { type: Array, default: () => [] },
    errors: { type: Array, default: () => [] },
    max_items: { type: String, default: '9' },
    baseline_title: { type: String, default: 'Baseline Period' },
    reporting_title: { type: String, default: 'Reporting years' },
    reporting_subtitle: { type: String, default: '' },
    start_year_label: { type: String, default: 'Start Year' },
    end_year_label: { type: String, default: 'End Year' },
    asset_label: { type: String, default: 'Asset' },
    year_label: { type: String, default: 'Year' }
  },
  
  data() {
    return {
      // Vue manages UI state directly
    };
  },
  
  computed: {
    baselineBase() {
      return this.v_model.baseline?.base || { asset: null, year: null };
    },
    
    baselineReport() {
      return this.v_model.baseline?.report || { asset: null, year: null };
    },
    
    reportingItems() {
      // Convert reporting items (excluding baseline) to array
      const items = [];
      
      Object.keys(this.v_model).forEach(key => {
        if (key !== 'baseline') {
          const value = this.v_model[key];
          if (value && typeof value === 'object') {
            const id = parseInt(key);
            items.push({
              id,
              asset: value.asset || null,
              year: value.year || null
            });
          }
        }
      });
      
      return items.sort((a, b) => a.id - b.id);
    },
    
    sortedItemsAsc() {
      return [...this.items].sort((a, b) => {
        const aVal = a.value || a;
        const bVal = b.value || b;
        return aVal < bVal ? -1 : aVal > bVal ? 1 : 0;
      });
    },
    
    sortedItemsDesc() {
      return [...this.items].sort((a, b) => {
        const aVal = a.value || a;
        const bVal = b.value || b;
        return aVal > bVal ? -1 : aVal < bVal ? 1 : 0;
      });
    },
    
    yearItems() {
      const currentYear = new Date().getFullYear();
      const years = [];
      
      for (let year = 2000; year <= currentYear + 5; year++) {
        years.push({ text: year.toString(), value: year });
      }
      
      return years.reverse();
    },
    
    yearItemsDesc() {
      const currentYear = new Date().getFullYear();
      const years = [];
      
      for (let year = currentYear + 5; year >= 2000; year--) {
        years.push({ text: year.toString(), value: year });
      }
      
      return years;
    }
  },
  
  mounted() {
    console.log('CustomListB mounted with items:', this.items);
    
    // Ensure baseline structure exists reactively
    this.initializeBaseline();
  },
  
  methods: {
    // Validation helper methods for inline error display
    hasBaselineError(period, field) {
      return this.errors.some(error => 
        error === `Asset required for baseline ${period}` && field === 'asset' ||
        error === `Year required for baseline ${period}` && field === 'year' ||
        error === 'Start year must be before end year in baseline period' && (period === 'base' || period === 'report') && field === 'year'
      );
    },
    
    getBaselineError(period, field) {
      const hasAssetError = this.errors.some(error => error === `Asset required for baseline ${period}` && field === 'asset');
      const hasYearError = this.errors.some(error => error === `Year required for baseline ${period}` && field === 'year');
      const hasOrderError = this.errors.some(error => error === 'Start year must be before end year in baseline period' && field === 'year');
      
      if (hasAssetError) return ['Required'];
      if (hasYearError) return ['Required'];
      if (hasOrderError) return ['Start year must be before end year'];
      return [];
    },
    
    hasReportingError(itemId, field) {
      return this.errors.some(error => 
        error === `Asset required for reporting year ${itemId}` && field === 'asset' ||
        error === `Year required for reporting year ${itemId}` && field === 'year'
      );
    },
    
    getReportingError(itemId, field) {
      const hasAssetError = this.errors.some(error => error === `Asset required for reporting year ${itemId}` && field === 'asset');
      const hasYearError = this.errors.some(error => error === `Year required for reporting year ${itemId}` && field === 'year');
      
      if (hasAssetError) return ['Required'];
      if (hasYearError) return ['Required'];
      return [];
    },
    
    initializeBaseline() {
      // Use $set for reactive baseline initialization
      if (!this.v_model.baseline) {
        this.$set(this.v_model, 'baseline', {
          base: { asset: null, year: null },
          report: { asset: null, year: null }
        });
      }
    },
    
    updateBaseline(period, field, value) {
      // Ensure baseline structure exists reactively
      if (!this.v_model.baseline) {
        this.$set(this.v_model, 'baseline', {
          base: { asset: null, year: null },
          report: { asset: null, year: null }
        });
      }
      
      // Ensure period exists
      if (!this.v_model.baseline[period]) {
        this.$set(this.v_model.baseline, period, { asset: null, year: null });
      }
      
      // Update the specific field reactively
      this.$set(this.v_model.baseline[period], field, value);
    },
    
    updateReportingItem(id, field, value) {
      // Ensure reporting item exists
      if (!this.v_model[id]) {
        this.$set(this.v_model, id, { asset: null, year: null });
      }
      
      // Update the specific field reactively
      this.$set(this.v_model[id], field, value);
    },
    
    addReportingItem() {
      // Calculate next ID for reporting items (skip 'baseline')
      const reportingIds = Object.keys(this.v_model)
        .filter(k => k !== 'baseline')
        .map(k => parseInt(k))
        .filter(n => !isNaN(n));
      
      const nextId = reportingIds.length > 0 ? Math.max(...reportingIds) + 1 : 2;
      
      // Check max items limit
      if (reportingIds.length >= parseInt(this.max_items)) {
        return;
      }
      
      // Add new reporting item reactively using $set
      this.$set(this.v_model, nextId, { asset: null, year: null });
    },
    
    removeReportingItem(id) {
      // Don't allow removing if it's the last reporting item
      const reportingIds = Object.keys(this.v_model).filter(k => k !== 'baseline');
      if (reportingIds.length <= 1) {
        return;
      }
      
      // Remove reporting item reactively using $delete
      this.$delete(this.v_model, id);
    },
    
    resetComponent() {
      // Clear all properties reactively
      Object.keys(this.v_model).forEach(key => {
        this.$delete(this.v_model, key);
      });
      
      // Reinitialize with baseline structure and one reporting item
      this.$set(this.v_model, 'baseline', {
        base: { asset: null, year: null },
        report: { asset: null, year: null }
      });
      this.$set(this.v_model, 2, { asset: null, year: null });
      
      // Also emit reset event to Python backend if needed
      this.$emit('vue_reset');
    },
    
    // Method to completely replace v_model from Python
    jupyter_set_model(newModel) {
      console.log('📥 Jupyter set_model called with:', newModel);
      
      // Clear all existing keys
      const existingKeys = Object.keys(this.v_model);
      existingKeys.forEach(key => {
        this.$delete(this.v_model, key);
      });
      
      // Set all new keys reactively
      Object.keys(newModel).forEach(key => {
        this.$set(this.v_model, key, newModel[key]);
      });
      
      console.log('✅ Model completely replaced reactively');
    },
    
    // Simple test method to check if Python->Vue communication works
    test_method(data) {
      console.log('🧪 Test method called from Python with:', data);
      alert('Test method works!');
    }
  }
};
</script>