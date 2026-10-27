import 'package:plugin_platform_interface/plugin_platform_interface.dart';
import 'package:url_launcher_platform_interface/link.dart';
import 'package:url_launcher_platform_interface/url_launcher_platform_interface.dart';

/// Simulated `url_launcher` platform: records what the app tries to open and
/// never touches the system.
class FakeUrlLauncher extends UrlLauncherPlatform
    with MockPlatformInterfaceMixin {
  FakeUrlLauncher({this.result = true, this.throws = false});

  final bool result;
  final bool throws;
  final launched = <String>[];
  final modes = <PreferredLaunchMode>[];

  @override
  LinkDelegate? get linkDelegate => null;

  @override
  Future<bool> launchUrl(String url, LaunchOptions options) async {
    launched.add(url);
    modes.add(options.mode);
    if (throws) throw Exception('sin navegador');
    return result;
  }

  @override
  Future<bool> canLaunch(String url) async => true;
}
