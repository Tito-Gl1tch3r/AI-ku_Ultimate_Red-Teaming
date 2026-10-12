#include "model/HexDocumentModel.h"

#include "core/PerformanceTrace.h"

#include <QStringList>

#include <algorithm>
#include <utility>

namespace {

constexpr qsizetype kBytesPerRow = 16;

} // namespace

HexDocumentModel::HexDocumentModel(QObject* parent)
    : QAbstractListModel(parent)
{
}

int HexDocumentModel::rowCount(const QModelIndex& parent) const
{
    if (parent.isValid()) {
        return 0;
    }
    return static_cast<int>((bytes_.size() + kBytesPerRow - 1) / kBytesPerRow);
}

QVariant HexDocumentModel::data(const QModelIndex& index, int role) const
{
    if (!index.isValid() || index.row() < 0 || index.row() >= rowCount()) {
        return {};
    }

    const qsizetype offset = static_cast<qsizetype>(index.row()) * kBytesPerRow;
    switch (role) {
    case AddressRole:
        return addressForOffset(offset);
    case BytesRole:
        return bytesForOffset(offset);
    case AsciiRole:
        return asciiForOffset(offset);
    default:
        return {};
    }
}

QHash<int, QByteArray> HexDocumentModel::roleNames() const
{
    return {
        { AddressRole, "address" },
        { BytesRole, "bytes" },
        { AsciiRole, "ascii" }
    };
}

QString HexDocumentModel::path() const
{
    return path_;
}

QString HexDocumentModel::kind() const
{
    return kind_;
}

qulonglong HexDocumentModel::size() const
{
    return static_cast<qulonglong>(bytes_.size());
}

unsigned char HexDocumentModel::byteAt(qsizetype offset) const
{
    if (offset < 0 || offset >= bytes_.size()) {
        return 0U;
    }
    return static_cast<unsigned char>(bytes_.at(offset));
}

void HexDocumentModel::setDocument(QString path, QString kind, QByteArray bytes)
{
    PerformanceTrace trace(QStringLiteral("HexDocumentModel::setDocument"));

    beginResetModel();
    path_ = std::move(path);
    kind_ = std::move(kind);
    bytes_ = std::move(bytes);
    endResetModel();
    emit documentChanged();
}

void HexDocumentModel::clear()
{
    if (path_.isEmpty() && kind_.isEmpty() && bytes_.isEmpty()) {
        return;
    }

    beginResetModel();
    path_.clear();
    kind_.clear();
    bytes_.clear();
    endResetModel();
    emit documentChanged();
}

QString HexDocumentModel::addressForOffset(qsizetype offset) const
{
    return QStringLiteral("%1").arg(static_cast<qulonglong>(offset), 8, 16, QLatin1Char('0')).toUpper();
}

QStringList HexDocumentModel::bytesForOffset(qsizetype offset) const
{
    QStringList result;
    result.reserve(kBytesPerRow);
    const qsizetype end = std::min(offset + kBytesPerRow, bytes_.size());
    for (qsizetype i = offset; i < end; ++i) {
        const auto value = static_cast<unsigned char>(bytes_.at(i));
        result.append(QStringLiteral("%1").arg(value, 2, 16, QLatin1Char('0')).toUpper());
    }
    return result;
}

QString HexDocumentModel::asciiForOffset(qsizetype offset) const
{
    QString result;
    result.reserve(kBytesPerRow);
    const qsizetype end = std::min(offset + kBytesPerRow, bytes_.size());
    for (qsizetype i = offset; i < end; ++i) {
        const auto value = static_cast<unsigned char>(bytes_.at(i));
        result += value >= 32U && value <= 126U
            ? QLatin1Char(static_cast<char>(value))
            : QLatin1Char('.');
    }
    return result;
}
