import 'package:flutter/material.dart' as material;

import 'app_localizations.dart';

export 'package:flutter/material.dart' hide SelectableText, Text;

class Text extends material.StatelessWidget {
  const Text(
    this.data, {
    super.key,
    this.style,
    this.strutStyle,
    this.textAlign,
    this.textDirection,
    this.locale,
    this.softWrap,
    this.overflow,
    this.textScaler,
    this.maxLines,
    this.semanticsLabel,
    this.textWidthBasis,
    this.textHeightBehavior,
    this.selectionColor,
    this.localize = true,
  });

  final String data;
  final material.TextStyle? style;
  final material.StrutStyle? strutStyle;
  final material.TextAlign? textAlign;
  final material.TextDirection? textDirection;
  final material.Locale? locale;
  final bool? softWrap;
  final material.TextOverflow? overflow;
  final material.TextScaler? textScaler;
  final int? maxLines;
  final String? semanticsLabel;
  final material.TextWidthBasis? textWidthBasis;
  final material.TextHeightBehavior? textHeightBehavior;
  final material.Color? selectionColor;
  final bool localize;

  @override
  material.Widget build(material.BuildContext context) => material.Text(
    localize ? tr(data) : data,
    style: style,
    strutStyle: strutStyle,
    textAlign: textAlign,
    textDirection: textDirection,
    locale: locale,
    softWrap: softWrap,
    overflow: overflow,
    textScaler: textScaler,
    maxLines: maxLines,
    semanticsLabel: semanticsLabel == null ? null : tr(semanticsLabel!),
    textWidthBasis: textWidthBasis,
    textHeightBehavior: textHeightBehavior,
    selectionColor: selectionColor,
  );
}

class SelectableText extends material.StatelessWidget {
  const SelectableText(
    this.data, {
    super.key,
    this.style,
    this.textAlign,
    this.localize = true,
  });

  final String data;
  final material.TextStyle? style;
  final material.TextAlign? textAlign;
  final bool localize;

  @override
  material.Widget build(material.BuildContext context) =>
      material.SelectableText(
        localize ? tr(data) : data,
        style: style,
        textAlign: textAlign,
      );
}
