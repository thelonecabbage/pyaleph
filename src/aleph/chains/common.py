from aleph.storage import get_json, pin_add
from aleph.model.messages import Message

import logging
LOGGER = logging.getLogger('chains.common')


async def get_verification_buffer(message):
    """ Returns a serialized string to verify the message integrity
    (this is was it signed)
    """
    return '{chain}\n{sender}\n{type}\n{item_hash}'.format(**message)\
        .encode('utf-8')


async def mark_confirmed_data(chain_name, tx_hash, height):
    """ Returns data required to mark a particular hash as confirmed
    in underlying chain.
    """
    return {
        'confirmed': True,
        'confirmations': [  # TODO: we should add the current one there
                            # and not replace it.
            {'chain': chain_name,
             'height': height,
             'hash': tx_hash}]}


async def incoming(message, chain_name=None,
                   tx_hash=None, height=None, seen_ids=None):
    """ New incoming message from underlying chain.
    Will be marked as confirmed if existing in database, created if not.
    """
    hash = message['item_hash']

    if hash in seen_ids:
        # is it really what we want here?
        return

    LOGGER.info("Incoming %s." % hash)

    # we set the incoming chain as default for signature
    message['chain'] = message.get('chain', chain_name)

    # TODO: verify if search key is ok. do we need an unique key for messages?
    existing = await Message.collection.find_one({
        'item_hash': hash,
        'chain': message['chain'],
        'sender': message['sender'],
        'type': message['type']
    }, projection={'confirmed': 1, 'confirmations': 1})

    # new_values = {'confirmed': False}  # this should be our default.
    new_values = {}
    if chain_name and tx_hash and height:
        # We are getting a confirmation here
        new_values = await mark_confirmed_data(chain_name, tx_hash, height)

    if existing:
        if seen_ids is not None:
            if hash in seen_ids:
                # is it really what we want here?
                return
            else:
                seen_ids.append(hash)

        if (existing['confirmed'] and
                chain_name in [c['chain'] for c in existing['confirmations']]):
            return

        LOGGER.info("Updating %s." % hash)

        if chain_name and tx_hash and height:
            # we need to update messages adding the confirmation
            await Message.collection.update_many({
                'item_hash': hash,
                'chain': message['chain'],
                'sender': message['sender']
            }, {
                '$set': {
                    'confirmed': True
                },
                '$addToSet': {
                    'confirmations': new_values['confirmations'][0]
                }
            })

    else:
        if not (chain_name and tx_hash and height):
            new_values = {'confirmed': False}  # this should be our default.

        try:
            content = await get_json(hash)
        except Exception:
            LOGGER.exception("Can't get content of object %r" % hash)
            return

        if content.get('address', None) is None:
            content['address'] = message['sender']

        if content.get('time', None) is None:
            content['time'] = message['time']

        # for now, only support direct signature
        # (no 3rd party or multiple address signing)
        if message['sender'] != content['address']:
            LOGGER.warn("Invalid sender for %s" % hash)
            return

        if seen_ids is not None:
            if hash in seen_ids:
                # is it really what we want here?
                return
            else:
                seen_ids.append(hash)

        LOGGER.info("New message to store for %s." % hash)
        message.update(new_values)
        message['content'] = content
        await Message.collection.insert(message)

        # since it's on-chain, we need to keep that content.
        LOGGER.debug("Pining hash %s" % hash)
        await pin_add(hash)


async def invalidate(chain_name, block_height):
    """ Invalidates a particular block height from an underlying chain
    (in case of forks)
    """
    pass


async def get_content_to_broadcast(messages):
    return {'protocol': 'aleph',
            'version': 1,
            'content': {
                'messages': messages
            }}
