#include "presentation/HexViewerItem.h"

#include <QFont>
#include <QFontMetricsF>
#include <QPainter>

#include <algorithm>
#include <array>
#include <cmath>

namespace {

constexpr int kBytesPerRow = 16;
constexpr qreal kFontPixelSize = 12.0;
constexpr qreal kRowHeight = 22.0;
constexpr qreal kLeftMargin = 14.0;
constexpr qreal kRightMargin = 14.0;
constexpr qreal kAddressWidth = 92.0;
constexpr qreal kByteWidth = 34.0;
constexpr qreal kAsciiWidth = 150.0;
constexpr qreal kTableWidth = kAddressWidth + kByteWidth * kBytesPerRow + kAsciiWidth + kLeftMargin + kRightMargin + 16.0;

const QColor kBackgroundColor(QStringLiteral("#0f1318"));
const QColor kAlternateRowColor(QStringLiteral("#111820"));
const QColor kAddressColor(QStringLiteral("#7ab7ff"));
const QColor kByteColor(QStringLiteral("#d7e0ea"));
const QColor kMutedByteColor(QStringLiteral("#66707b"));
const QColor kAsciiColor(QStringLiteral("#c8d1dc"));

QFont hexFont()
{
    QFont font(QStringLiteral("Consolas"));
    font.setPixelSize(static_cast<int>(kFontPixelSize));
    font.setStyleHint(QFont::Monospace);
    font.setFixedPitch(true);
    return font;
}

QString hexByte(unsigned char value)
{
    static constexpr std::array<char, 16> kDigits {
        '0', '1', '2', '3', '4', '5', '6', '7',
        '8', '9', 'A', 'B', 'C', 'D', 'E', 'F'
    };

    QString text;
    text.resize(2);
    text[0] = QLatin1Char(kDigits.at(value >> 4U));
    text[1] = QLatin1Char(kDigits.at(value & 0x0FU));
    return text;
}

QString addressText(qsizetype offset)
{
    return QStringLiteral("%1").arg(static_cast<qulonglong>(offset), 8, 16, QLatin1Char('0')).toUpper();
}

QChar asciiChar(unsigned char value)
{
    return value >= 32U && value <= 126U
        ? QLatin1Char(static_cast<char>(value))
        : QLatin1Char('.');
}

} // namespace

HexViewerItem::HexViewerItem(QQuickItem* parent)
    : QQuickPaintedItem(parent)
{
    setAntialiasing(false);
    setOpaquePainting(true);
    refreshMetrics();
}

HexDocumentModel* HexViewerItem::model() const
{
    return model_;
}

void HexViewerItem::setModel(HexDocumentModel* model)
{
    if (model_ == model) {
        return;
    }

    if (model_ != nullptr) {
        disconnect(modelConnection_);
    }

    model_ = model;
    if (model_ != nullptr) {
        modelConnection_ = connect(model_, &HexDocumentModel::documentChanged, this, [this] {
            refreshMetrics();
            update();
        });
    } else {
        modelConnection_ = {};
    }

    refreshMetrics();
    update();
    emit modelChanged();
}

qreal HexViewerItem::scrollY() const
{
    return scrollY_;
}

void HexViewerItem::setScrollY(qreal scrollY)
{
    scrollY = std::max<qreal>(0.0, scrollY);
    if (qFuzzyCompare(scrollY_ + 1.0, scrollY + 1.0)) {
        return;
    }

    scrollY_ = scrollY;
    update();
    emit scrollYChanged();
}

qreal HexViewerItem::documentWidth() const
{
    return documentWidth_;
}

qreal HexViewerItem::documentHeight() const
{
    return documentHeight_;
}

void HexViewerItem::paint(QPainter* painter)
{
    painter->fillRect(boundingRect(), kBackgroundColor);
    if (model_ == nullptr || model_->size() == 0U) {
        return;
    }

    const QFont font = hexFont();
    const QFontMetricsF metrics(font);
    const qreal baseline = (kRowHeight - metrics.height()) / 2.0 + metrics.ascent();
    painter->setFont(font);

    const int rows = rowCount();
    const int firstVisibleRow = std::max(0, static_cast<int>(std::floor(scrollY_ / kRowHeight)) - 1);
    const int lastVisibleRow = std::min(rows - 1, static_cast<int>(std::ceil((scrollY_ + height()) / kRowHeight)) + 1);

    for (int row = firstVisibleRow; row <= lastVisibleRow; ++row) {
        const qreal y = static_cast<qreal>(row) * kRowHeight - scrollY_;
        if (y > height()) {
            break;
        }
        if (y + kRowHeight < 0.0) {
            continue;
        }

        painter->fillRect(QRectF(0.0, y, width(), kRowHeight), row % 2 == 0 ? kBackgroundColor : kAlternateRowColor);

        const qsizetype rowOffset = static_cast<qsizetype>(row) * kBytesPerRow;
        painter->setPen(kAddressColor);
        painter->drawText(QPointF(kLeftMargin, y + baseline), addressText(rowOffset));

        QString ascii;
        ascii.reserve(kBytesPerRow);
        for (int column = 0; column < kBytesPerRow; ++column) {
            const qsizetype offset = rowOffset + column;
            if (static_cast<qulonglong>(offset) >= model_->size()) {
                break;
            }

            const unsigned char value = model_->byteAt(offset);
            painter->setPen(value == 0U ? kMutedByteColor : kByteColor);
            const qreal x = kLeftMargin + kAddressWidth + static_cast<qreal>(column) * kByteWidth;
            painter->drawText(QRectF(x, y, kByteWidth, kRowHeight), Qt::AlignHCenter | Qt::AlignVCenter, hexByte(value));
            ascii.append(asciiChar(value));
        }

        painter->setPen(kAsciiColor);
        const qreal asciiX = kLeftMargin + kAddressWidth + kByteWidth * kBytesPerRow;
        painter->drawText(QPointF(asciiX, y + baseline), ascii);
    }
}

void HexViewerItem::refreshMetrics()
{
    const qreal oldWidth = documentWidth_;
    const qreal oldHeight = documentHeight_;
    documentWidth_ = kTableWidth;
    documentHeight_ = static_cast<qreal>(rowCount()) * kRowHeight;

    if (!qFuzzyCompare(oldWidth + 1.0, documentWidth_ + 1.0)
        || !qFuzzyCompare(oldHeight + 1.0, documentHeight_ + 1.0)) {
        emit documentMetricsChanged();
    }
}

int HexViewerItem::rowCount() const
{
    if (model_ == nullptr) {
        return 0;
    }
    return model_->rowCount();
}
