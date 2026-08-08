import 'package:flutter_test/flutter_test.dart';
import 'package:video_indirici/l10n/app_localizations.dart';
import 'package:video_indirici/l10n/localized_material.dart';

void main() {
  tearDown(() => setAppLanguage('tr'));

  test('static and dynamic strings are translated to English', () {
    setAppLanguage('en');
    expect(tr('İndir'), 'Download');
    expect(tr('12 video içinde ara'), '12 videos');
    expect(tr('3 geçmiş kaydı silindi.'), '3 history records deleted.');
    expect(
      tr('4 öğe kuyruğa eklendi, 2 etkin tekrar atlandı'),
      '4 items added to the queue, 2 active duplicates skipped',
    );
    expect(tr('Harika video kaydı'), 'Harika video kaydı');
  });

  testWidgets('localized Text rebuilds with the selected language', (
    tester,
  ) async {
    setAppLanguage('en');
    await tester.pumpWidget(
      const MaterialApp(home: Scaffold(body: Text('Kuyruk'))),
    );
    expect(find.text('Queue'), findsOneWidget);
    expect(find.text('Kuyruk'), findsNothing);
  });
}
