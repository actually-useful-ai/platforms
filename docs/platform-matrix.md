# Platform Matrix

| Platform | Adapter id | Primary artifact | Detection | Notes |
|---|---|---|---|---|
| KDP | `kdp` | EPUB + print/cover bundle | `book.yml` | Manual upload only |
| Pebble | `pebble` | `.pbw` | package markers / platforms.yml | rePebble CLI |
| Android | `android` | APK/AAB | Gradle/manifest | Shared primitives |
| Fire Tablet | `fire-tablet` | APK | Android spine | Amazon store manual |
| Fire TV | `fire-tv` | APK | Leanback checks | D-pad required |
| Android TV | `android-tv` | APK | Leanback checks | Separate track from Fire TV |
| Vega | `vega` | vendor package | explicit only | Isolated from Fire OS |
| webOS | `webos` | `.ipk` | appinfo/www | ares-package |
| Tizen | `tizen` | `.wgt`/Tizen pkg | config.xml | Studio often required |
| Roku | `roku` | channel zip | manifest/brs | Native SceneGraph |
| Web kiosk | `web-kiosk` | static bundle | www/index.html | Offline validation |
