# EDGEiQ MAP Final Spec Audit V1

- PASS: RIGHT_TO_LEFT_ORIENTATION - MAP visual carries the Victorian right-to-left orientation marker.
- PASS: CURATED_TRACK_ASSET - MAP resolves and renders the curated selected-track map asset where available.
- PASS: STRAIGHT_BLUE_LANES - Lane bars are straight horizontal blue lines controlled by a left position variable.
- PASS: LABEL_STRUCTURE - Runner labels contain saddlecloth number, speed value/unavailable state, and horse name.
- PASS: NO_COLOURED_NUMBER_CHIPS - Saddlecloth numbers use neutral white styling rather than coloured chips.
- PASS: SCRATCHINGS_COMPRESS_IN_SERVICE - Scratched runners are filtered in the map service before display; React does not recalculate barriers.
- PASS: HONEST_UNAVAILABLE_POSITIONING - Unavailable speed evidence renders without a lane instead of fabricating position.
- PASS: NO_CONFIDENCE_COPY - MAP component has no product-facing confidence copy.
- PASS: NO_PROHIBITED_MAP_PATTERNS - Component does not introduce prohibited MAP patterns.
