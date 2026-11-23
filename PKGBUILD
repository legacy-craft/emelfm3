pkgname=emelfm3
pkgver=1.0
pkgrel=1
pkgdesc="Lightweight single-file orthodox dual-pane file manager in Python 3 and GTK 3"
arch=('any')
url="https://github.com/legacy-craft/emelfm3"
license=('GPL-3.0-only')
depends=('python' 'python-gobject' 'gtk3')
source=("$pkgname-$pkgver.tar.gz::$url/archive/refs/tags/v$pkgver.tar.gz")
sha256sums=('9cdb1426180fce9fbd19d5f7f581783a2f9ae1abb38b5f7c424894c8d28567d1')

package() {
    cd "$srcdir/$pkgname-$pkgver"
    install -Dm755 emelfm3.py "$pkgdir/usr/bin/emelfm3"
    install -Dm644 emelfm3.desktop "$pkgdir/usr/share/applications/emelfm3.desktop"
    install -Dm644 LICENSE "$pkgdir/usr/share/licenses/$pkgname/LICENSE"
}
