#ifndef REARK_HEX_DOCUMENT_MODEL_H
#define REARK_HEX_DOCUMENT_MODEL_H

#include <QAbstractListModel>
#include <QByteArray>
#include <QString>

class HexDocumentModel : public QAbstractListModel {
    Q_OBJECT
    Q_PROPERTY(QString path READ path NOTIFY documentChanged)
    Q_PROPERTY(QString kind READ kind NOTIFY documentChanged)
    Q_PROPERTY(qulonglong size READ size NOTIFY documentChanged)

public:
    enum Role {
        AddressRole = Qt::UserRole + 1,
        BytesRole,
        AsciiRole
    };

    explicit HexDocumentModel(QObject* parent = nullptr);

    [[nodiscard]] int rowCount(const QModelIndex& parent = QModelIndex()) const override;
    [[nodiscard]] QVariant data(const QModelIndex& index, int role = Qt::DisplayRole) const override;
    [[nodiscard]] QHash<int, QByteArray> roleNames() const override;

    [[nodiscard]] QString path() const;
    [[nodiscard]] QString kind() const;
    [[nodiscard]] qulonglong size() const;
    [[nodiscard]] unsigned char byteAt(qsizetype offset) const;

    void setDocument(QString path, QString kind, QByteArray bytes);
    void clear();

signals:
    void documentChanged();

private:
    [[nodiscard]] QString addressForOffset(qsizetype offset) const;
    [[nodiscard]] QStringList bytesForOffset(qsizetype offset) const;
    [[nodiscard]] QString asciiForOffset(qsizetype offset) const;

    QString path_;
    QString kind_;
    QByteArray bytes_;
};

#endif // REARK_HEX_DOCUMENT_MODEL_H
