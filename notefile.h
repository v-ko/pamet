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

#ifndef NOTEFILE_H
#define NOTEFILE_H

#include "note.h"
#include "util.h"
#include <QObject>

class MisliDir;

class NoteFile : public QObject
{
    Q_OBJECT

    Q_PROPERTY(QString filePath READ filePath WRITE setPathAndLoad NOTIFY filePathChanged)

public:
    //Functions
    NoteFile();
    ~NoteFile();

    QString name();
    Note *getFirstSelectedNote();
    Note *getLowestIdNote();
    Note *getNoteById(int id);
    void selectAllNotes();
    void clearNoteSelection();
    void clearLinkSelection();
    int linkSelectedNotesTo(Note *nt);
    void arrangeLinksGeometry(Note *nt);
    void checkForInvalidLinks(Note *nt);

    void makeCoordsRelativeTo(double x,double y);
    void makeAllIDsNegative();
    int getNewId();

    void addNote(Note* nt);
    Note *loadNote(Note* nt);
    Note *cloneNote(Note* nt);
    void deleteSelected();

    int loadFromFilePath();
    int loadFromIniString(QString fileString);
    void loadFromJsonString(QString jsonString);
    bool loadFileAsJson();
    QString toIniString();
    QString toJsonString();

    void saveStateToHistory();
    void saveLastInHistoryToFile();
    void undo();
    void redo();

    //Properties
    QString filePath();

    //Variables
    QList<Note*> notes; //all the notes are stored here
    int lastNoteId;
    std::vector<QString> comment; //the comments in the file
    QString filePath_m; //note file path
    double eyeX, eyeY, eyeZ; //camera position for the GUI cases (can't be QPointF, it has z)
    QStringList undoHistory, redoHistory; //The current state is on the back of undoHistory
    bool isDisplayedFirstOnStartup;
    bool isTimelineNoteFile;
    bool isReadable;
    bool saveWithRequest;
    bool keepHistoryViaGit;
    bool indexedForSearch;

signals:
    //Property changes
    void filePathChanged(QString);

    //Other
    void visualChange();
    void requestingSave(NoteFile*);
    void noteTextChanged(NoteFile*);

public slots:
    //Set properties
    void setPathAndLoad(QString newPath);

    //Other
    void save();
    void arrangeLinksGeometry();
};

#endif // NOTEFILE_H
