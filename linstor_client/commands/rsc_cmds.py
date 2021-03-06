import linstor_client.argparse.argparse as argparse

import linstor
import linstor_client
import linstor.sharedconsts as apiconsts
from linstor_client.commands import Commands, DrbdOptions, ArgumentError
from linstor_client.consts import NODE_NAME, RES_NAME, STORPOOL_NAME, Color, ExitCode
from linstor_client.utils import Output, namecheck


class ResourceCommands(Commands):
    _resource_headers = [
        linstor_client.TableHeader("ResourceName"),
        linstor_client.TableHeader("Node"),
        linstor_client.TableHeader("Port"),
        linstor_client.TableHeader("State", Color.DARKGREEN, alignment_text='>')
    ]

    def __init__(self):
        super(ResourceCommands, self).__init__()

    def setup_commands(self, parser):
        """

        :param argparse.ArgumentParser parser:
        :return:
        """

        subcmds = [
            Commands.Subcommands.Create,
            Commands.Subcommands.List,
            Commands.Subcommands.ListVolumes,
            Commands.Subcommands.Delete,
            Commands.Subcommands.SetProperty,
            Commands.Subcommands.ListProperties,
            Commands.Subcommands.DrbdPeerDeviceOptions
        ]

        # Resource subcommands
        res_parser = parser.add_parser(
            Commands.RESOURCE,
            aliases=["r"],
            formatter_class=argparse.RawTextHelpFormatter,
            description="Resouce subcommands")
        res_subp = res_parser.add_subparsers(
            title="resource commands",
            metavar="",
            description=Commands.Subcommands.generate_desc(subcmds)
        )

        # new-resource
        p_new_res = res_subp.add_parser(
            Commands.Subcommands.Create.LONG,
            aliases=[Commands.Subcommands.Create.SHORT],
            description='Deploys a resource definition to a node.')
        p_new_res.add_argument(
            '--storage-pool', '-s',
            type=namecheck(STORPOOL_NAME),
            help="Storage pool name to use.").completer = self.storage_pool_dfn_completer
        p_new_res.add_argument('--diskless', '-d', action="store_true", help='Should the resource be diskless')
        p_new_res.add_argument(
            '--async',
            action='store_true',
            help='Do not wait for deployment on satellites before returning'
        )
        p_new_res.add_argument(
            '--auto-place',
            type=int,
            metavar="REPLICA_COUNT",
            help = 'Auto place a resource to a specified number of nodes'
        )
        p_new_res.add_argument(
            '--do-not-place-with',
            type=namecheck(RES_NAME),
            nargs='+',
            metavar="RESOURCE_NAME",
            help='Try to avoid nodes that already have a given resource deployed.'
        ).completer = self.resource_completer
        p_new_res.add_argument(
            '--do-not-place-with-regex',
            type=str,
            metavar="RESOURCE_REGEX",
            help='Try to avoid nodes that already have a resource ' +
                 'deployed whos name is matching the given regular expression.'
        )
        p_new_res.add_argument(
            '--replicas-on-same',
            nargs='+',
            default=[],
            metavar="AUX_NODE_PROPERTY",
            help='Tries to place resources on nodes with the same given auxiliary node property values.'
        )
        p_new_res.add_argument(
            '--replicas-on-different',
            nargs='+',
            default=[],
            metavar="AUX_NODE_PROPERTY",
            help='Tries to place resources on nodes with a different value for the given auxiliary node property.'
        )
        p_new_res.add_argument(
            '--diskless-on-remaining',
            action="store_true",
            help='Will add a diskless resource on all non replica nodes.'
        )
        p_new_res.add_argument(
            'node_name',
            type=namecheck(NODE_NAME),
            nargs='*',
            help='Name of the node to deploy the resource').completer = self.node_completer
        p_new_res.add_argument(
            'resource_definition_name',
            type=namecheck(RES_NAME),
            help='Name of the resource definition').completer = self.resource_dfn_completer
        p_new_res.set_defaults(func=self.create)

        # remove-resource
        p_rm_res = res_subp.add_parser(
            Commands.Subcommands.Delete.LONG,
            aliases=[Commands.Subcommands.Delete.SHORT],
            description='Removes a resource. '
            'The resource is undeployed from the node '
            "and the resource entry is marked for removal from linstor's data "
            'tables. After the node has undeployed the resource, the resource '
            "entry is removed from linstor's data tables.")
        p_rm_res.add_argument('-q', '--quiet', action="store_true",
                              help='Unless this option is used, linstor will issue a safety question '
                              'that must be answered with yes, otherwise the operation is canceled.')
        p_rm_res.add_argument(
            '--async',
            action='store_true',
            help='Do not wait for deployment on satellites before returning'
        )
        p_rm_res.add_argument('node_name',
                              nargs="+",
                              help='Name of the node').completer = self.node_completer
        p_rm_res.add_argument('name',
                              help='Name of the resource to delete').completer = self.resource_completer
        p_rm_res.set_defaults(func=self.delete)

        resgroupby = [x.name for x in ResourceCommands._resource_headers]
        res_group_completer = Commands.show_group_completer(resgroupby, "groupby")

        p_lreses = res_subp.add_parser(
            Commands.Subcommands.List.LONG,
            aliases=[Commands.Subcommands.List.SHORT],
            description='Prints a list of all resource definitions known to '
            'linstor. By default, the list is printed as a human readable table.')
        p_lreses.add_argument('-p', '--pastable', action="store_true", help='Generate pastable output')
        p_lreses.add_argument(
            '-g', '--groupby',
            nargs='+',
            choices=resgroupby).completer = res_group_completer
        p_lreses.add_argument(
            '-r', '--resources',
            nargs='+',
            type=namecheck(RES_NAME),
            help='Filter by list of resources').completer = self.resource_completer
        p_lreses.add_argument(
            '-n', '--nodes',
            nargs='+',
            type=namecheck(NODE_NAME),
            help='Filter by list of nodes').completer = self.node_completer
        p_lreses.set_defaults(func=self.list)

        # list volumes
        p_lvlms = res_subp.add_parser(
            Commands.Subcommands.ListVolumes.LONG,
            aliases=[Commands.Subcommands.ListVolumes.SHORT],
            description='Prints a list of all volumes.'
        )
        p_lvlms.add_argument('-p', '--pastable', action="store_true", help='Generate pastable output')
        p_lvlms.add_argument(
            '-n', '--nodes',
            nargs='+',
            type=namecheck(NODE_NAME),
            help='Filter by list of nodes').completer = self.node_completer
        p_lvlms.add_argument('-s', '--storpools', nargs='+', type=namecheck(STORPOOL_NAME),
                             help='Filter by list of storage pools').completer = self.storage_pool_completer
        p_lvlms.add_argument(
            '-r', '--resources',
            nargs='+',
            type=namecheck(RES_NAME),
            help='Filter by list of resources').completer = self.resource_completer
        p_lvlms.set_defaults(func=self.list_volumes)

        # show properties
        p_sp = res_subp.add_parser(
            Commands.Subcommands.ListProperties.LONG,
            aliases=[Commands.Subcommands.ListProperties.SHORT],
            description="Prints all properties of the given resource.")
        p_sp.add_argument('-p', '--pastable', action="store_true", help='Generate pastable output')
        p_sp.add_argument(
            'node_name',
            help="Node name where the resource is deployed.").completer = self.node_completer
        p_sp.add_argument(
            'resource_name',
            help="Resource name").completer = self.resource_completer
        p_sp.set_defaults(func=self.print_props)

        # set properties
        p_setprop = res_subp.add_parser(
            Commands.Subcommands.SetProperty.LONG,
            aliases=[Commands.Subcommands.SetProperty.SHORT],
            description='Sets properties for the given resource on the given node.')
        p_setprop.add_argument(
            'node_name',
            type=namecheck(NODE_NAME),
            help='Node name where resource is deployed.').completer = self.node_completer
        p_setprop.add_argument(
            'name',
            type=namecheck(RES_NAME),
            help='Name of the resource'
        ).completer = self.resource_completer
        Commands.add_parser_keyvalue(p_setprop, "resource")
        p_setprop.set_defaults(func=self.set_props)

        # drbd peer device options
        p_drbd_peer_opts = res_subp.add_parser(
            Commands.Subcommands.DrbdPeerDeviceOptions.LONG,
            aliases=[Commands.Subcommands.DrbdPeerDeviceOptions.SHORT],
            description="Set drbd peer-device options."
        )
        p_drbd_peer_opts.add_argument(
            'node_a',
            type=namecheck(NODE_NAME),
            help="1. Node in the node connection"
        ).completer = self.node_completer
        p_drbd_peer_opts.add_argument(
            'node_b',
            type=namecheck(NODE_NAME),
            help="1. Node in the node connection"
        ).completer = self.node_completer
        p_drbd_peer_opts.add_argument(
            'resource_name',
            type=namecheck(RES_NAME),
            help="Resource name"
        ).completer = self.resource_completer

        DrbdOptions.add_arguments(
            p_drbd_peer_opts,
            [x for x in DrbdOptions.drbd_options()['options']
                if DrbdOptions.drbd_options()['options'][x]['category'] == 'peer-device-options']
        )
        p_drbd_peer_opts.set_defaults(func=self.drbd_peer_opts)

        self.check_subcommands(res_subp, subcmds)

    @staticmethod
    def _satellite_not_connected(replies):
        return any(reply.ret_code & apiconsts.WARN_NOT_CONNECTED == apiconsts.WARN_NOT_CONNECTED for reply in replies)

    def create(self, args):
        all_replies = []
        if args.auto_place:
            # auto-place resource
            all_replies = self._linstor.resource_auto_place(
                args.resource_definition_name,
                args.auto_place,
                args.storage_pool,
                args.do_not_place_with,
                args.do_not_place_with_regex,
                [linstor.consts.NAMESPC_AUXILIARY + '/' + x for x in args.replicas_on_same],
                [linstor.consts.NAMESPC_AUXILIARY + '/' + x for x in args.replicas_on_different],
                diskless_on_remaining=args.diskless_on_remaining
            )

            if not self._linstor.all_api_responses_success(all_replies):
                return self.handle_replies(args, all_replies)

            if not args.async:
                def event_handler(event_header, event_data):
                    if event_header.event_name == apiconsts.EVENT_RESOURCE_DEFINITION_READY:
                        if event_header.event_action == apiconsts.EVENT_STREAM_CLOSE_REMOVED:
                            print((Output.color_str('ERROR:', Color.RED, args.no_color)) + " Resource removed")
                            return ExitCode.API_ERROR

                        if event_data is not None:
                            if event_data.error_count > 0:
                                return ExitCode.API_ERROR

                            if event_data.ready_count == args.auto_place:
                                return ExitCode.OK

                    return None

                watch_result = self._linstor.watch_events(
                    self._linstor.return_if_failure,
                    event_handler,
                    linstor.ObjectIdentifier(resource_name=args.resource_definition_name)
                )

                if isinstance(watch_result, list):
                    all_replies += watch_result
                    if not self._linstor.all_api_responses_success(watch_result):
                        return self.handle_replies(args, all_replies)
                elif watch_result != ExitCode.OK:
                    return watch_result

        else:
            # normal create resource
            # check that node is given
            if not args.node_name:
                raise ArgumentError("resource create: too few arguments: Node name missing.")

            for node_name in args.node_name:
                all_replies += self._linstor.resource_create(
                    node_name,
                    args.resource_definition_name,
                    args.diskless,
                    args.storage_pool
                )

                if not self._linstor.all_api_responses_success(all_replies):
                    return self.handle_replies(args, all_replies)

            def event_handler(event_header, event_data):
                if event_header.node_name == node_name:
                    if event_header.event_name in [
                            apiconsts.EVENT_RESOURCE_STATE,
                            apiconsts.EVENT_RESOURCE_DEPLOYMENT_STATE
                    ]:
                        if event_header.event_action == apiconsts.EVENT_STREAM_CLOSE_NO_CONNECTION:
                            print(Output.color_str('WARNING:', Color.YELLOW, args.no_color) +
                                  " Satellite connection lost")
                            return ExitCode.NO_SATELLITE_CONNECTION
                        if event_header.event_action == apiconsts.EVENT_STREAM_CLOSE_REMOVED:
                            print((Output.color_str('ERROR:', Color.RED, args.no_color)) + " Resource removed")
                            return ExitCode.API_ERROR

                    if event_header.event_name == apiconsts.EVENT_RESOURCE_STATE and \
                            event_data is not None and event_data.ready:
                        return ExitCode.OK

                    return self.check_failure_events(event_header.event_name, event_data)

                return None

            if not ResourceCommands._satellite_not_connected(all_replies) and not args.async:
                for node_name in args.node_name:

                    watch_result = self._linstor.watch_events(
                        self._linstor.return_if_failure,
                        event_handler,
                        linstor.ObjectIdentifier(node_name=node_name, resource_name=args.resource_definition_name)
                    )

                    if isinstance(watch_result, list):
                        all_replies += watch_result
                        if not self._linstor.all_api_responses_success(watch_result):
                            return self.handle_replies(args, all_replies)
                    elif watch_result != ExitCode.OK:
                        return watch_result

        return self.handle_replies(args, all_replies)

    @classmethod
    def check_failure_events(cls, event_name, event_data):
        if event_name == apiconsts.EVENT_RESOURCE_DEPLOYMENT_STATE and event_data is not None:
            api_call_responses = [
                linstor.ApiCallResponse(response)
                for response in event_data.responses
            ]
            failure_responses = [
                api_call_response for api_call_response in api_call_responses
                if not api_call_response.is_success()
            ]

            return failure_responses if failure_responses else None
        return None

    def delete(self, args):
        if args.async:
            # execute delete resource and flatten result list
            replies = [x for subx in args.node_name for x in self._linstor.resource_delete(subx, args.name)]
            return self.handle_replies(args, replies)
        else:
            def event_handler(event_header, event_data):
                if event_header.event_name in [apiconsts.EVENT_RESOURCE_DEPLOYMENT_STATE]:
                    if event_header.event_action == apiconsts.EVENT_STREAM_CLOSE_NO_CONNECTION:
                        print(Output.color_str('WARNING:', Color.YELLOW, args.no_color) +
                              " Satellite connection lost")
                        return ExitCode.NO_SATELLITE_CONNECTION
                    if event_header.event_action == apiconsts.EVENT_STREAM_CLOSE_REMOVED:
                        return [linstor.ApiCallResponse(response) for response in event_data.responses]

                    return self.check_failure_events(event_header.event_name, event_data)
                return None

            all_delete_replies = []
            for node in args.node_name:
                replies = self.get_linstorapi().resource_delete(node, args.name)
                all_delete_replies += replies

                if not self._linstor.all_api_responses_success(replies):
                    return self.handle_replies(args, all_delete_replies)

                watch_result = self.get_linstorapi().watch_events(
                    self._linstor.return_if_failure,
                    event_handler,
                    linstor.ObjectIdentifier(node_name=node, resource_name=args.name)
                )

                if isinstance(watch_result, list):
                    all_delete_replies += watch_result
                    if not self._linstor.all_api_responses_success(watch_result):
                        return self.handle_replies(args, all_delete_replies)
                elif watch_result != ExitCode.OK:
                    return watch_result

            return self.handle_replies(args, all_delete_replies)

    @staticmethod
    def find_rsc_state(rsc_states, rsc_name, node_name):
        for rscst in rsc_states:
            if rscst.rsc_name == rsc_name and rscst.node_name == node_name:
                return rscst
        return None

    def show(self, args, lstmsg):
        rsc_dfns = self._linstor.resource_dfn_list()
        if isinstance(rsc_dfns[0], linstor.ApiCallResponse):
            return self.handle_replies(args, rsc_dfns)
        rsc_dfns = rsc_dfns[0].proto_msg.rsc_dfns

        rsc_dfn_map = {x.rsc_name: x for x in rsc_dfns}

        tbl = linstor_client.Table(utf8=not args.no_utf8, colors=not args.no_color, pastable=args.pastable)
        for hdr in ResourceCommands._resource_headers:
            tbl.add_header(hdr)

        tbl.set_groupby(args.groupby if args.groupby else [ResourceCommands._resource_headers[0].name])

        for rsc in lstmsg.resources:
            rsc_dfn = rsc_dfn_map[rsc.name]
            marked_delete = apiconsts.FLAG_DELETE in rsc.rsc_flags
            rsc_state_proto = ResourceCommands.find_rsc_state(lstmsg.resource_states, rsc.name, rsc.node_name)
            rsc_state = tbl.color_cell("Unknown", Color.YELLOW)
            if marked_delete:
                rsc_state = tbl.color_cell("DELETING", Color.RED)
            elif rsc_state_proto:
                if rsc_state_proto.HasField('in_use') and rsc_state_proto.in_use:
                    rsc_state = tbl.color_cell("InUse", Color.GREEN)
                else:
                    for vlm in rsc.vlms:
                        vlm_state = ResourceCommands.get_volume_state(rsc_state_proto.vlm_states,
                                                                      vlm.vlm_nr) if rsc_state_proto else None
                        state_txt, color = self.volume_state_cell(vlm_state, rsc.rsc_flags, vlm.vlm_flags)
                        rsc_state = tbl.color_cell(state_txt, color)
                        if color is not None:
                            break
            tbl.add_row([
                rsc.name,
                rsc.node_name,
                rsc_dfn.rsc_dfn_port,
                rsc_state
            ])
        tbl.show()

    def list(self, args):
        lstmsg = self._linstor.resource_list(filter_by_nodes=args.nodes, filter_by_resources=args.resources)
        return self.output_list(args, lstmsg, self.show)

    @staticmethod
    def get_resource_state(res_states, node_name, resource_name):
        for rsc_state in res_states:
            if rsc_state.node_name == node_name and rsc_state.rsc_name == resource_name:
                return rsc_state
        return None

    @staticmethod
    def get_volume_state(volume_states, volume_nr):
        for volume_state in volume_states:
            if volume_state.vlm_nr == volume_nr:
                return volume_state
        return None

    @staticmethod
    def volume_state_cell(vlm_state, rsc_flags, vlm_flags):
        """
        Determains the status of a drbd volume for table display.

        :param vlm_state: vlm_state proto
        :param rsc_flags: rsc flags
        :param vlm_flags: vlm flags
        :return: A tuple (state_text, color)
        """
        tbl_color = None
        state_prefix = 'Resizing, ' if apiconsts.FLAG_RESIZE in vlm_flags else ''
        state = state_prefix + "Unknown"
        if vlm_state and vlm_state.HasField("disk_state") and vlm_state.disk_state:
            disk_state = vlm_state.disk_state

            if disk_state == 'DUnknown':
                state = state_prefix + "Unknown"
                tbl_color = Color.YELLOW
            elif disk_state == 'Diskless':
                if apiconsts.FLAG_DISKLESS not in rsc_flags:  # unintentional diskless
                    state = state_prefix + disk_state
                    tbl_color = Color.RED
                else:
                    state = state_prefix + disk_state  # green text
            elif disk_state in ['Inconsistent', 'Failed']:
                state = state_prefix + disk_state
                tbl_color = Color.RED
            elif disk_state in ['UpToDate']:
                state = state_prefix + disk_state  # green text
            else:
                state = state_prefix + disk_state
                tbl_color = Color.YELLOW
        else:
            tbl_color = Color.YELLOW
        return state, tbl_color

    @classmethod
    def show_volumes(cls, args, lstmsg):
        tbl = linstor_client.Table(utf8=not args.no_utf8, colors=not args.no_color, pastable=args.pastable)
        tbl.add_column("Node")
        tbl.add_column("Resource")
        tbl.add_column("StoragePool")
        tbl.add_column("VolumeNr")
        tbl.add_column("MinorNr")
        tbl.add_column("DeviceName")
        tbl.add_column("State", color=Output.color(Color.DARKGREEN, args.no_color), just_txt='>')

        for rsc in lstmsg.resources:
            rsc_state = ResourceCommands.get_resource_state(lstmsg.resource_states, rsc.node_name, rsc.name)
            for vlm in rsc.vlms:
                vlm_state = ResourceCommands.get_volume_state(rsc_state.vlm_states, vlm.vlm_nr) if rsc_state else None
                state_txt, color = cls.volume_state_cell(vlm_state, rsc.rsc_flags, vlm.vlm_flags)
                state = tbl.color_cell(state_txt, color) if color else state_txt
                tbl.add_row([
                    rsc.node_name,
                    rsc.name,
                    vlm.stor_pool_name,
                    str(vlm.vlm_nr),
                    str(vlm.vlm_minor_nr),
                    vlm.device_path,
                    state
                ])

        tbl.show()

    def list_volumes(self, args):
        lstmsg = self._linstor.volume_list(args.nodes, args.storpools, args.resources)

        return self.output_list(args, lstmsg, self.show_volumes)

    @classmethod
    def _props_list(cls, args, lstmsg):
        result = []
        if lstmsg:
            for rsc in lstmsg.resources:
                if rsc.name == args.resource_name and rsc.node_name == args.node_name:
                    result.append(rsc.props)
                    break
        return result

    def print_props(self, args):
        lstmsg = self._linstor.resource_list()

        return self.output_props_list(args, lstmsg, self._props_list)

    def set_props(self, args):
        args = self._attach_aux_prop(args)
        mod_prop_dict = Commands.parse_key_value_pairs([args.key + '=' + args.value])
        replies = self._linstor.resource_modify(
            args.node_name,
            args.name,
            mod_prop_dict['pairs'],
            mod_prop_dict['delete']
        )
        return self.handle_replies(args, replies)

    def drbd_peer_opts(self, args):
        a = DrbdOptions.filter_new(args)
        del a['resource-name']
        del a['node-a']
        del a['node-b']

        mod_props, del_props = DrbdOptions.parse_opts(a)

        replies = self._linstor.resource_conn_modify(
            args.resource_name,
            args.node_a,
            args.node_b,
            mod_props,
            del_props
        )
        return self.handle_replies(args, replies)

    @staticmethod
    def completer_volume(prefix, **kwargs):
        possible = set()
        return possible
