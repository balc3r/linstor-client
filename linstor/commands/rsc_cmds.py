from proto.MsgCrtRsc_pb2 import MsgCrtRsc
from proto.MsgDelRsc_pb2 import MsgDelRsc
from proto.MsgLstRsc_pb2 import MsgLstRsc
from proto.LinStorMapEntry_pb2 import LinStorMapEntry
from linstor.commcontroller import need_communication, completer_communication
from linstor.commands import Commands
from linstor.sharedconsts import (
    API_CRT_RSC,
    API_DEL_RSC,
    API_LST_RSC,
    KEY_STOR_POOL_NAME
)


class ResourceCommands(Commands):

    @staticmethod
    @need_communication
    def create(cc, args):
        p = MsgCrtRsc()
        p.rsc_name = args.name
        p.node_name = args.node_name

        if args.storage_pool:
            prop = LinStorMapEntry()
            prop.key = KEY_STOR_POOL_NAME
            prop.value = args.storage_pool
            p.rsc_props.extend([prop])

        return Commands._create(cc, API_CRT_RSC, p)

    @staticmethod
    @need_communication
    def delete(cc, args):
        del_msgs = []
        for node_name in args.node_name:
            p = MsgDelRsc()
            p.rsc_name = args.name
            p.node_name = node_name

            del_msgs.append(p)

        Commands._delete(cc, args, API_DEL_RSC, del_msgs)

        return None

    @staticmethod
    @need_communication
    def list(cc, args):
        lstmsg = Commands._get_list_message(cc, API_LST_RSC, MsgLstRsc(), args)

        if lstmsg:
            prntfrm = "{rsc:<20s} {uuid:<40s} {node:<30s}"
            print(prntfrm.format(rsc="Resource-name", uuid="UUID", node="Node"))
            for rsc in lstmsg.resources:
                print(prntfrm.format(
                    rsc=rsc.name,
                    uuid=rsc.uuid,
                    node=rsc.node_name))

        return None

    @staticmethod
    @completer_communication
    def completer(cc, prefix, **kwargs):
        possible = set()
        lstmsg = Commands._get_list_message(cc, API_LST_RSC, MsgLstRsc())

        if lstmsg:
            for rsc in lstmsg.resources:
                possible.add(rsc.name)

            if prefix:
                return [res for res in possible if res.startswith(prefix)]

        return possible
