// The window contract, graded on the files that carry it — so the three things the
// owner saw regress on 2026-09-16 cannot regress silently again:
//   1. full screen: the Android window is edge to edge (the nav bar must not own a band)
//   2. the keyboard OVERLAYS the avatar: nothing may resize the window or the body
//   3. the canvas never moves for the keyboard; only the chrome column lifts
// Each arm reads the shipped source and asserts the exact token, because a rebuild
// from a tree missing any one of these looks fine on an iPhone and wrong on a Galaxy.
import 'dart:io';
import 'package:flutter_test/flutter_test.dart';

String _read(String p) => File(p).readAsStringSync();

void main() {
  final manifest = _read('android/app/src/main/AndroidManifest.xml');
  final main = _read('lib/main.dart');
  final v29 = File('android/app/src/main/res/values-v29/styles.xml');

  test('the window is edge to edge on Android', () {
    expect(main, contains('SystemUiMode.edgeToEdge'),
        reason: 'without this the Android window stops above the navigation bar and the chrome sits in a band');
    expect(v29.existsSync(), isTrue, reason: 'values-v29/styles.xml carries enforceNavigationBarContrast=false');
    expect(_read(v29.path), contains('android:enforceNavigationBarContrast">false'),
        reason: 'Android 10+ forces an opaque scrim behind a 3-button bar unless the theme says not to');
  });

  test('the keyboard overlays the avatar — nothing resizes for it', () {
    expect(manifest, contains('android:windowSoftInputMode="adjustNothing"'),
        reason: 'adjustResize shrinks the activity window by the keyboard height');
    expect(manifest, isNot(contains('adjustResize')));
    expect(main, contains('resizeToAvoidBottomInset: false'),
        reason: "Scaffold's default shrinks the body even when the window does not");
  });

  test('only the chrome lifts with the keyboard; the canvas is not inside the lifted subtree', () {
    // The AnimatedPadding that follows viewInsets must wrap the chrome (SafeArea →
    // Column → PromptCapsule), and the AvatarCanvasFit must sit OUTSIDE it, in the
    // Stack body. If the canvas ever ends up inside the padded subtree it will move.
    final pad = main.indexOf('padding: EdgeInsets.only(bottom: keyboard)');
    final canvas = main.indexOf('AvatarCanvasFit(');
    final capsule = main.indexOf('PromptCapsule(');
    expect(pad, greaterThan(0), reason: 'the chrome column must lift by the keyboard inset');
    expect(canvas, lessThan(pad), reason: 'the canvas is laid out before, and outside, the lifted chrome');
    expect(capsule, greaterThan(pad), reason: 'the capsule is inside the lifted chrome');
  });
}
