<template>
  <v-card class="ma-2">
    
    <v-card-text>      
      <div v-for="(item, index) in modelItems" :key="item.id" class="mb-4">
        <v-row align="center">
          <!-- Asset ID Selection - Uses most space -->
          <v-col cols="9">
            <v-select
              :value="item.asset"
              @input="updateItem(index, 'asset', $event)"
              :items="items"
              :label="asset_label"
              dense
              placeholder="GEE Asset ID"
              :error="hasAssetError(item.id)"
              :error-messages="getAssetError(item.id)"
              class="mr-2"
            />
          </v-col>
          
          <!-- Year Selection - Fixed width -->
          <v-col cols="2">
            <v-select
              :value="item.year"
              @input="updateItem(index, 'year', $event)"
              :items="yearItems"
              :label="year_label"
              dense
              :error="hasYearError(item.id)"
              :error-messages="getYearError(item.id)"
              class="mr-2"
            />
          </v-col>
          
          <!-- Actions -->
          <v-col cols="1" class="d-flex justify-center">
            <!-- Add button always appears on first element -->
            <v-btn
              v-if="index === 0"
              icon
              @click="addItem"
              :disabled="modelItems.length >= parseInt(max_items) + 1"
            >
              <v-icon>mdi-plus</v-icon>
            </v-btn>
            
            <!-- Remove button appears on all elements except the first -->
            <v-btn
              v-if="index > 0"
              icon
              @click="removeItem(index)"
            >
              <v-icon>mdi-minus</v-icon>
            </v-btn>
          </v-col>
        </v-row>
        
        <v-divider v-if="index < modelItems.length - 1" class="my-2" />
      </div>
      
      <!-- Remove the additional add button section since + is always on first element -->
      
    </v-card-text>
  </v-card>
</template>

<script>
export default {
  name: 'CustomListA',
  
  props: {
    v_model: { type: Object, default: () => ({}) },
    items: { type: Array, default: () => [] },
    years: { type: Array, default: () => [] },
    errors: { type: Array, default: () => [] },
    max_items: { type: String, default: '9' },
    title: { type: String, default: 'Reporting years' },
    asset_label: { type: String, default: 'Asset' },
    year_label: { type: String, default: 'Year' }
  },
  
  data() {
    return {
      // Track next ID for new items
    };
  },
  
  computed: {
    modelItems() {
      // Convert v_model object to array for easier template iteration
      const items = [];

      console.log('Computing modelItems from v_model:', this.v_model);
      // log out the items prop as well
      console.log('Items prop:', this.items);

      
      // Sort keys numerically and create items
      // Don't filter out items with null/undefined values - they're valid empty items!
      const sortedKeys = Object.keys(this.v_model || {})
        .sort((a, b) => parseInt(a) - parseInt(b));
      
      for (const key of sortedKeys) {
        const value = this.v_model[key];
        // Accept any object, even if fields are null
        if (value && typeof value === 'object') {
          items.push({
            id: parseInt(key),
            asset: value.asset || null,
            year: value.year || null
          });
        }
      }
      
      // Ensure at least one item exists
      if (items.length === 0) {
        items.push({ id: 1, asset: null, year: null });
      }
      
      return items;
    },
    
    yearItems() {
      // Generate year options (you can customize this range)
      const currentYear = new Date().getFullYear();
      const years = [];
      
      for (let year = 2000; year <= currentYear + 5; year++) {
        years.push({ text: year.toString(), value: year });
      }
      
      return years.reverse(); // Most recent first
    }
  },
  
  mounted() {
    // Initialize with first item if v_model is empty using Vue's reactivity system
    if (Object.keys(this.v_model).length === 0) {
      this.$set(this.v_model, 1, { asset: null, year: null });
    }
    
    console.log('CustomListA mounted with v_model:', this.v_model);
    console.log('CustomListA mounted with items:', this.items);
  },
  
  methods: {
    // Validation helper methods for inline error display
    hasAssetError(itemId) {
      return this.errors.some(error => 
        error === `Asset required for item ${itemId}`
      );
    },
    
    getAssetError(itemId) {
      const hasError = this.errors.some(error => 
        error === `Asset required for item ${itemId}`
      );
      return hasError ? ['Required'] : [];
    },
    
    hasYearError(itemId) {
      return this.errors.some(error => 
        error === `Year required for item ${itemId}`
      );
    },
    
    getYearError(itemId) {
      const hasError = this.errors.some(error => 
        error === `Year required for item ${itemId}`
      );
      return hasError ? ['Required'] : [];
    },
    
    updateItem(index, field, value) {
      const item = this.modelItems[index];
      
      // Ensure the item exists in v_model using Vue's reactivity
      if (!this.v_model[item.id]) {
        this.$set(this.v_model, item.id, {});
      }
      
      // Update the field using Vue's reactivity system
      this.$set(this.v_model[item.id], field, value);
    },
    
    addItem() {
      console.log('🔥 addItem called!');
      
      // Check max items limit
      if (Object.keys(this.v_model).length >= parseInt(this.max_items) + 1) {
        console.log('❌ Max items reached');
        return;
      }
      
      // Calculate next ID
      const existingIds = Object.keys(this.v_model).map(k => parseInt(k)).filter(n => !isNaN(n));
      const nextId = existingIds.length > 0 ? Math.max(...existingIds) + 1 : 1;
      
      // Add new item using Vue's reactivity system
      this.$set(this.v_model, nextId, { asset: null, year: null });
      
      console.log('✅ Added item with id:', nextId);
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
    
    removeItem(index) {
      const item = this.modelItems[index];
      
      // Don't allow removing the last item
      if (Object.keys(this.v_model).length <= 1) {
        return;
      }
      
      // Remove item using Vue's reactivity system
      this.$delete(this.v_model, item.id);
    },
    
    resetComponent() {
      // Reset v_model to initial state using Vue's reactivity
      Object.keys(this.v_model).forEach(key => {
        this.$delete(this.v_model, key);
      });
      this.$set(this.v_model, 1, { asset: null, year: null });
      
      // Also emit reset event to Python backend if needed
      this.$emit('vue_reset');
    }
  }
};
</script>