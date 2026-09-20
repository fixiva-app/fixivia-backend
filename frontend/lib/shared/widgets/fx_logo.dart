import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';

class FxLogo extends StatelessWidget {
  const FxLogo({this.white = false, this.height = 28, super.key});

  final bool white;
  final double height;

  @override
  Widget build(BuildContext context) {
    final asset = white
        ? 'assets/branding/Fixiva_Logo_white.svg'
        : 'assets/branding/Fixiva_Logo.svg';
    return SvgPicture.asset(asset, height: height, fit: BoxFit.contain);
  }
}
