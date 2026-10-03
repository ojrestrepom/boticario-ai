import 'plant.dart';

/// The catalog currently contains plants only; [oils] intentionally matches
/// no records rather than inferring oil identities from plant parts.
enum PlantFilter { all, plants, oils }

/// Returns matching original plant objects in their original order.
List<Plant> searchPlants(
  Iterable<Plant> plants, {
  String query = '',
  PlantFilter filter = PlantFilter.all,
}) {
  final normalizedQuery = _normalize(query);
  if (filter == PlantFilter.oils) return const <Plant>[];

  return List<Plant>.unmodifiable(
    plants.where((plant) {
      if (filter == PlantFilter.plants && plant.kind != PlantKind.plant) {
        return false;
      }
      if (normalizedQuery.isEmpty) return true;
      return _normalize(plant.editorialCommonName).contains(normalizedQuery) ||
          _normalize(plant.sourceScientificName).contains(normalizedQuery);
    }),
  );
}

String _normalize(String value) {
  final collapsedWhitespace = value.trim().replaceAll(RegExp(r'\s+'), ' ');
  final decomposed = collapsedWhitespace.toLowerCase().replaceAllMapped(
    RegExp(r'[áàäâãåāăąčćďéèëêēėęěíìïîīįñńóòöôõōřŕšśťúùüûūůýÿžźżæœçğłđþ]'),
    (match) => _latinBase[match[0]] ?? match[0]!,
  );
  // Removing combining marks after decomposing common precomposed Latin
  // letters also handles decomposed input (for example "a\u0301").
  return decomposed.replaceAll(RegExp(r'[\u0300-\u036f]'), '');
}

const _latinBase = <String, String>{
  'á': 'a',
  'à': 'a',
  'ä': 'a',
  'â': 'a',
  'ã': 'a',
  'å': 'a',
  'ā': 'a',
  'ă': 'a',
  'ą': 'a',
  'č': 'c',
  'ć': 'c',
  'ď': 'd',
  'é': 'e',
  'è': 'e',
  'ë': 'e',
  'ê': 'e',
  'ē': 'e',
  'ė': 'e',
  'ę': 'e',
  'ě': 'e',
  'í': 'i',
  'ì': 'i',
  'ï': 'i',
  'î': 'i',
  'ī': 'i',
  'į': 'i',
  'ñ': 'n',
  'ń': 'n',
  'ó': 'o',
  'ò': 'o',
  'ö': 'o',
  'ô': 'o',
  'õ': 'o',
  'ō': 'o',
  'ř': 'r',
  'ŕ': 'r',
  'š': 's',
  'ś': 's',
  'ť': 't',
  'ú': 'u',
  'ù': 'u',
  'ü': 'u',
  'û': 'u',
  'ū': 'u',
  'ů': 'u',
  'ý': 'y',
  'ÿ': 'y',
  'ž': 'z',
  'ź': 'z',
  'ż': 'z',
  'æ': 'ae',
  'œ': 'oe',
  'ç': 'c',
  'ğ': 'g',
  'ł': 'l',
  'đ': 'd',
  'þ': 'th',
};
