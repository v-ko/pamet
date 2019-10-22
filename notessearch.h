/*  This file is part of Misli.

    Misli is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    Misli is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with Misli.  If not, see <http://www.gnu.org/licenses/>.
*/

#ifndef NOTESSEARCH_H
#define NOTESSEARCH_H

#include <QAbstractListModel>

#include "misliinstance.h"

class NotesSearch : public QAbstractListModel
{
    Q_OBJECT
public:
    struct SearchItem{
        MisliDir *md;
        NoteFile *nf;
        Note *nt;
        double probability;
        QString text;
    };

    //Functions
    NotesSearch(MisliWindow *misli_window, double initial_probability);
    int loadNotes();
    int loadNotes(MisliDir * misliDir, double initial_probability);
    int loadNotes(NoteFile * noteFile, MisliDir *misliDir, double initial_probability);
    static bool compareItems(SearchItem first,SearchItem second);

    //Variables
    QList<SearchItem> searchItems,searchResults;
    double initialProbability;
    MisliWindow *misliWindow;

signals:
    void searchComplete(QString string);
    
public slots:
    int rowCount(const QModelIndex &) const;
    QVariant data(const QModelIndex & index, int role = Qt::DisplayRole) const;
    void findByText(QString searchString);
};

#endif // NOTESSEARCH_H
