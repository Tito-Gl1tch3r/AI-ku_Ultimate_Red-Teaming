import { defineStore } from 'pinia';
import { ref } from 'vue';

export const useUiStore = defineStore('ui', () => {
  // State
  const hoveredAircraft = ref(null);
  const aircraftFilter = ref(''); // Filter applied from aircraft aggregate table
  const selectedAircraft = ref(new Set()); // Set of hex codes for selected aircraft

  // Actions
  const setHoveredAircraft = (hex) => {
    hoveredAircraft.value = hex;
  };

  const setAircraftFilter = (filter) => {
    aircraftFilter.value = filter || '';
  };

  const setSelectedAircraft = (hexSet) => {
    selectedAircraft.value = hexSet;
  };

  const toggleAircraftSelection = (hex) => {
    const newSet = new Set(selectedAircraft.value);
    if (newSet.has(hex)) {
      newSet.delete(hex);
    } else {
      newSet.add(hex);
    }
    selectedAircraft.value = newSet;
  };

  const isAircraftSelected = (hex) => {
    return selectedAircraft.value.has(hex);
  };

  return {
    // State
    hoveredAircraft,
    aircraftFilter,
    selectedAircraft,
    // Actions
    setHoveredAircraft,
    setAircraftFilter,
    setSelectedAircraft,
    toggleAircraftSelection,
    isAircraftSelected,
  };
}); 