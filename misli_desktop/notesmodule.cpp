#include "notesmodule.h"
#include "timeline.h"

NotesModule::NotesModule(Timeline *timeline_):
    TimelineModule(timeline_),
    checkbox("Notes module")
{
    controlWidget = &checkbox;
    misliDir = new MisliDir("/sync/misli",true);
    loadNotes();
}

void NotesModule::loadNotes()
{
    notesForDisplay.clear();

    for(NoteFile *nf: misliDir->noteFiles())
    {
        for (Note *nt: nf->notes){
            if( abs( nt->timeMade.toMSecsSinceEpoch() - timeline->positionInMSecs ) < timeline->viewportSizeInMSecs/2){
                notesForDisplay.append(nt);
                //FIXME: adjust note size
            }
        }
    }
}
