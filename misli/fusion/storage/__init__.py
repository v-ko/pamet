# from copy import copy
# from typing import List, Union

# import fusion
# from fusion import Entity, Change
# from fusion.storage.in_memory_repository import InMemoryRepository
# from fusion.storage.repository import Repository

# log = fusion.get_logger(__name__)

# _repo: Repository = InMemoryRepository()


# def publish_entity_change(change: Change):
#     pamet.channels.entity_changes.push(change)
#     pamet.channels.entity_changes_by_id.push(change)
#     pamet.channels.entity_changes_by_parent_gid.push(change)


# @log.traced
# def repo():
#     return _repo


# @log.traced
# def set_repo(repo):
#     global _repo

#     log.info('Setting repo to %s' % repo.path)
#     _repo = repo


# def insert(entity_or_batch: Union[Entity, List[Entity]]):
#     batch = entity_or_batch
#     if not isinstance(entity_or_batch, list):
#         batch = [entity_or_batch]

#     _repo.insert(batch)
#     for entity in batch:
#         change = Change.CREATE(entity)
#         publish_entity_change(change)


# def remove(entity_or_batch: Union[Entity, List[Entity]]):
#     if not entity_or_batch:
#         raise Exception('Cannot delete a falsy object.')

#     batch = entity_or_batch
#     if not isinstance(entity_or_batch, list):
#         batch = [entity_or_batch]

#     _repo.remove(batch)
#     for entity in batch:
#         change = Change.DELETE(entity)
#         publish_entity_change(change)


# def update(entity_or_batch: Union[Entity, List[Entity]]):
#     batch = entity_or_batch
#     if not isinstance(entity_or_batch, list):
#         batch = [entity_or_batch]

#     for entity in batch:
#         old_state = find_one(gid=entity.gid())
#         if not old_state:
#             raise Exception(f'Cannot update missing entity {entity}')

#         change = Change.UPDATE(old_state, entity)
#         publish_entity_change(change)

#     _repo.update(batch)


# def find(**filter):
#     results = []
#     for item in _repo.find(**filter):
#         results.append(copy(item))
#     return results


# def find_one(**filter):
#     found = _repo.find(**filter)

#     for f in found:
#         return f

#     return None
