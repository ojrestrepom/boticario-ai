import 'dart:math' as math;

import 'plant_species_metadata.dart';

class PlantPrediction {
  const PlantPrediction(this.species, this.score);
  final PlantSpecies species;

  /// Relative softmax score over all 1081 classes; not calibrated confidence.
  final double score;
}

List<PlantPrediction> plantTopFive(
  List<double> logits,
  PlantSpeciesMetadata metadata,
) {
  if (logits.length != PlantSpeciesMetadata.classCount ||
      logits.any((value) => !value.isFinite)) {
    throw ArgumentError('Expected 1081 finite logits.');
  }
  final maxLogit = logits.reduce(math.max);
  final weights = logits.map((value) => math.exp(value - maxLogit)).toList();
  final sum = weights.reduce((a, b) => a + b);
  final indices = List.generate(logits.length, (index) => index)
    ..sort((a, b) {
      final order = logits[b].compareTo(logits[a]);
      return order == 0 ? a.compareTo(b) : order;
    });
  return List.unmodifiable(
    indices
        .take(5)
        .map(
          (index) =>
              PlantPrediction(metadata.classes[index], weights[index] / sum),
        ),
  );
}
